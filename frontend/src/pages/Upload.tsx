import { useState, type FormEvent } from "react";
import { ApiError, createSession } from "../api/client";
import type { Role } from "../api/types";
import { DATA_NOTICE, DISCLAIMER } from "../lib/notices";
import { messageFor } from "../lib/messages";

// Kiểm tra phía client chỉ để báo lỗi sớm. Backend mới là nơi quyết định (REJECTED async, hard byte cap).
const MAX_UPLOAD_MB = 10;
const ROLES: { value: Role; label: string; hint: string }[] = [
  { value: "EMPLOYEE", label: "Người lao động", hint: "Tìm điều khoản bất lợi cho người đi làm." },
  { value: "EMPLOYER", label: "Người sử dụng lao động", hint: "Tìm điều khoản bất lợi hoặc sai luật với phía công ty." },
];

interface Props { onCreated: (sessionId: string, role: Role) => void }

export default function Upload({ onCreated }: Props) {
  const [role, setRole] = useState<Role | null>(null); // không chọn sẵn: role là bắt buộc
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function pickFile(f: File | null) {
    setError(null);
    if (f && !/\.(pdf|docx)$/i.test(f.name)) { setFile(null); setError(messageFor("UNSUPPORTED_FILE_TYPE")); return; }
    if (f && f.size > MAX_UPLOAD_MB * 1024 * 1024) { setFile(null); setError(messageFor("FILE_TOO_LARGE")); return; }
    setFile(f);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!role) return setError(messageFor("ROLE_REQUIRED"));
    if (!file) return setError("Vui lòng chọn tệp hợp đồng.");
    setBusy(true); setError(null);
    try {
      const s = await createSession(role, file);
      onCreated(s.session_id, role);
    } catch (err) {
      setError(messageFor(err instanceof ApiError ? err.code : null));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <h1>Phân tích rủi ro hợp đồng lao động</h1>
      <p className="lead">Tải hợp đồng lên, chọn bạn đứng ở phía nào, hệ thống chỉ ra các điều khoản có rủi ro kèm căn cứ pháp lý.</p>

      <form onSubmit={submit} noValidate>
        <fieldset>
          <legend>Bạn là ai trong hợp đồng này?</legend>
          {ROLES.map((r) => (
            <label key={r.value} className={"choice" + (role === r.value ? " on" : "")}>
              <input type="radio" name="role" value={r.value} checked={role === r.value} onChange={() => { setRole(r.value); setError(null); }} />
              <span><strong>{r.label}</strong><small>{r.hint}</small></span>
            </label>
          ))}
        </fieldset>

        <div className="field">
          <label htmlFor="file">Tệp hợp đồng</label>
          <input id="file" type="file" accept=".pdf,.docx" onChange={(e) => pickFile(e.target.files?.[0] ?? null)} />
          <small>PDF hoặc DOCX có sẵn văn bản, tối đa {MAX_UPLOAD_MB} MB. Chưa hỗ trợ tệp scan hoặc ảnh.</small>
        </div>

        <p className="error" role="alert" aria-live="polite">{error}</p>
        <button type="submit" disabled={busy}>{busy ? "Đang tải lên…" : "Phân tích hợp đồng"}</button>
      </form>

      <aside className="notices" aria-label="Lưu ý">
        <p><strong>Lưu ý.</strong> {DISCLAIMER}</p>
        <p><strong>Dữ liệu của bạn.</strong> {DATA_NOTICE}</p>
      </aside>
    </main>
  );
}

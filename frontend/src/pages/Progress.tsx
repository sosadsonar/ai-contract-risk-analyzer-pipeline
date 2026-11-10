import { useEffect, useRef, useState } from "react";
import { ApiError, endSession, retry } from "../api/client";
import type { Role } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { messageFor } from "../lib/messages";
import { getStageName } from "../lib/stages";

interface Props {
    sessionId: string;
    role: Role;
    onCompleted: () => void;
    onReset: () => void;
}

export default function Progress({ sessionId, role, onCompleted, onReset }: Props) {
    const { status, pollError, restartPolling } = usePolling(sessionId);
    const [actionError, setActionError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);
    // Ref để tránh onCompleted bị gọi lại mỗi khi re-render (ví dụ onCompleted là lambda mới)
    const completedRef = useRef(false);

    useEffect(() => {
        if (status?.status === "COMPLETED" && !completedRef.current) {
            completedRef.current = true;
            onCompleted();
        }
    }, [status?.status]); // eslint-disable-line react-hooks/exhaustive-deps

    async function handleRetry() {
        setBusy(true);
        setActionError(null);
        try {
            const raw = await retry(sessionId);
            // Backend da tra du StatusResponse cho retry. Van giu mac dinh an toan
            // de restartPolling khong nhan undefined neu backend thay doi sau nay.
            const nextStatus: import("../api/types").StatusResponse = {
                session_id: raw.session_id ?? sessionId,
                status: raw.status ?? "PROCESSING",
                stage: raw.stage ?? null,
                manual_retry_count: raw.manual_retry_count ?? 0,
                progress: raw.progress ?? null,
                error_code: raw.error_code ?? null,
                updated_at: raw.updated_at ?? new Date().toISOString(),
            };
            restartPolling(nextStatus);
        } catch (err) {
            setActionError(messageFor(err instanceof ApiError ? err.code : null));
        } finally {
            setBusy(false);
        }
    }

    async function handleEnd() {
        setBusy(true);
        try {
            await endSession(sessionId);
        } catch {
            // Bỏ qua lỗi nếu phiên đã đóng trước đó
        } finally {
            setBusy(false);
            onReset();
        }
    }

    const currentStatus = status?.status ?? "UPLOADED";
    const prog = status?.progress;
    const percent = prog && prog.total_units > 0
        ? Math.min(100, Math.round((prog.completed_units / prog.total_units) * 100))
        : null;

    // SESSION_NOT_FOUND: polling đã dừng (xem usePolling), hiển thị nhánh riêng
    const isSessionNotFound = pollError === "SESSION_NOT_FOUND";

    return (
        <main className="page">
            <h1>Đang phân tích hợp đồng</h1>
            <p className="lead">
                Vai trò phân tích: <strong>{role === "EMPLOYEE" ? "Người lao động" : "Người sử dụng lao động"}</strong>
            </p>

            {/* Nhánh SESSION_NOT_FOUND: phiên không còn tồn tại */}
            {isSessionNotFound && (
                <section className="card card-danger" role="alert">
                    <h2>Không tìm thấy phiên làm việc</h2>
                    <p>{messageFor("SESSION_NOT_FOUND")}</p>
                    <div className="actions">
                        <button type="button" onClick={onReset}>Mở phiên mới</button>
                    </div>
                </section>
            )}

            {/* Nhánh đang chạy: UPLOADED / VALIDATING / PROCESSING */}
            {!isSessionNotFound && (currentStatus === "UPLOADED" || currentStatus === "VALIDATING" || currentStatus === "PROCESSING") && (
                <section className="card" aria-live="polite">
                    <p className="status-title">
                        {currentStatus === "VALIDATING" ? "Đang kiểm tra và tiền xử lý tài liệu…" : "Đang phân tích rủi ro pháp lý…"}
                    </p>
                    <p className="muted">
                        Bước hiện tại: <strong>{getStageName(status?.stage)}</strong>
                    </p>
                    {percent !== null && (
                        <div className="progress-wrap">
                            <div className="progress-bar" style={{ width: `${percent}%` }} />
                            <small>{prog!.completed_units} / {prog!.total_units} đơn vị ({percent}%)</small>
                        </div>
                    )}
                    {pollError && pollError !== "SESSION_NOT_FOUND" && <p className="error">{messageFor(pollError)}</p>}
                    <div className="actions">
                        <button type="button" className="btn-secondary" onClick={handleEnd} disabled={busy}>
                            Hủy và kết thúc phiên
                        </button>
                    </div>
                </section>
            )}

            {/* Nhánh REJECTED: trạng thái cuối, KHÔNG có nút Retry (DEC-02, TDD §5.9) */}
            {currentStatus === "REJECTED" && (
                <section className="card card-danger" role="alert">
                    <h2>Tài liệu không hợp lệ</h2>
                    <p>{messageFor(status?.error_code)}</p>
                    <p className="muted">{messageFor("REJECTED")}</p>
                    <div className="actions">
                        <button type="button" onClick={onReset}>Mở phiên mới</button>
                    </div>
                </section>
            )}

            {/* Nhánh FAILED: cho phép Retry thủ công tối đa 2 lần (FR-21) */}
            {currentStatus === "FAILED" && (
                <section className="card card-danger" role="alert">
                    <h2>Quá trình phân tích bị gián đoạn</h2>
                    <p>{messageFor(status?.error_code)}</p>
                    <p className="muted">
                        Số lần đã thử lại: {status?.manual_retry_count ?? 0} / 2
                    </p>
                    {actionError && <p className="error">{actionError}</p>}
                    <div className="actions">
                        {(status?.manual_retry_count ?? 0) < 2 && (
                            <button type="button" onClick={handleRetry} disabled={busy}>
                                {busy ? "Đang gửi yêu cầu…" : "Thử lại"}
                            </button>
                        )}
                        <button type="button" className="btn-secondary" onClick={handleEnd} disabled={busy}>
                            Mở phiên mới
                        </button>
                    </div>
                </section>
            )}

            {/* Nhánh EXPIRED */}
            {currentStatus === "EXPIRED" && (
                <section className="card" role="alert">
                    <h2>Phiên làm việc đã hết hạn</h2>
                    <p>{messageFor("EXPIRED")}</p>
                    <div className="actions">
                        <button type="button" onClick={onReset}>Mở phiên mới</button>
                    </div>
                </section>
            )}
        </main>
    );
}
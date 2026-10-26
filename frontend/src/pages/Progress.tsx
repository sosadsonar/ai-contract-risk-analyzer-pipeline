import { useEffect, useState } from "react";
import { ApiError, endSession, retry } from "../api/client";
import type { Role, Stage } from "../api/types";
import { usePolling } from "../hooks/usePolling";
import { messageFor } from "../lib/messages";

const STAGE_NAMES: Record<Stage, string> = {
    UPLOAD: "Đang nhận tệp hợp đồng",
    EXTRACTION: "Trích xuất và chuẩn hóa văn bản",
    SCOPE_PRECHECK: "Kiểm tra phạm vi hợp đồng lao động",
    PII_MASKING: "Ẩn thông tin cá nhân (PII)",
    SEGMENTATION: "Tách các điều khoản",
    CLAUSE_GRAPH: "Dựng đồ thị quan hệ điều khoản",
    CLAUSE_CLASSIFICATION: "Phân loại điều khoản (AI)",
    LEGAL_RETRIEVAL: "Đối chiếu kho văn bản pháp luật",
    RISK_ANALYSIS: "Phân tích rủi ro theo vai trò (AI)",
    CITATION_VALIDATION: "Kiểm증 trích dẫn điều luật",
    ASSEMBLY: "Tổng hợp báo cáo kết quả",
    EXPORT: "Chuẩn bị xuất báo cáo",
};

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

    useEffect(() => {
        if (status?.status === "COMPLETED") {
            onCompleted();
        }
    }, [status?.status, onCompleted]);

    async function handleRetry() {
        setBusy(true);
        setActionError(null);
        try {
            const nextStatus = await retry(sessionId);
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

    return (
        <main className="page">
            <h1>Đang phân tích hợp đồng</h1>
            <p className="lead">
                Vai trò phân tích: <strong>{role === "EMPLOYEE" ? "Người lao động" : "Người sử dụng lao động"}</strong>
            </p>

            {/* Nhánh đang chạy: UPLOADED / VALIDATING / PROCESSING */}
            {(currentStatus === "UPLOADED" || currentStatus === "VALIDATING" || currentStatus === "PROCESSING") && (
                <section className="card" aria-live="polite">
                    <p className="status-title">
                        {currentStatus === "VALIDATING" ? "Đang kiểm tra và tiền xử lý tài liệu…" : "Đang phân tích rủi ro pháp lý…"}
                    </p>
                    <p className="muted">
                        Bước hiện tại: <strong>{status?.stage ? STAGE_NAMES[status.stage] : "Khởi tạo phiên"}</strong>
                    </p>
                    {percent !== null && (
                        <div className="progress-wrap">
                            <div className="progress-bar" style={{ width: `${percent}%` }} />
                            <small>{prog!.completed_units} / {prog!.total_units} đơn vị ({percent}%)</small>
                        </div>
                    )}
                    {pollError && <p className="error">{messageFor(pollError)}</p>}
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
import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, endSession, exportReport, getResult } from "../api/client";
import type { Citation, FinalResult } from "../api/types";
import { clauseLabel } from "../lib/clauseLabel";
import { labelName } from "../lib/labels";
import { messageFor } from "../lib/messages";
import { DATA_NOTICE, DISCLAIMER } from "../lib/notices";
import { buildSegments } from "../lib/segments";
import { classifyRisk } from "../lib/riskView";

const REVIEW_MESSAGE = "Điều khoản này có thể có rủi ro nhưng hệ thống chưa kết luận được; cần xem xét thủ công";
const INSUFFICIENT_MESSAGE = "có thể có rủi ro, chưa đủ căn cứ trong kho luật, cần đọc kỹ";

interface Props {
    sessionId: string;
    onReset: () => void;
}

export default function Result({ sessionId, onReset }: Props) {
    const [data, setData] = useState<FinalResult | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [activeClauseId, setActiveClauseId] = useState<string | null>(null);
    const [exporting, setExporting] = useState(false);
    const cardRefs = useRef<Record<string, HTMLElement | null>>({});
    const textRefs = useRef<Record<string, HTMLElement | null>>({});

    useEffect(() => {
        let cancelled = false;
        getResult(sessionId)
            .then((res) => {
                if (cancelled) return;
                setData(res);
                if (res.risks.length > 0) setActiveClauseId(res.risks[0].clause_id);
            })
            .catch((err) => {
                if (cancelled) return;
                setError(messageFor(err instanceof ApiError ? err.code : null));
            });
        return () => { cancelled = true; };
    }, [sessionId]);

    const citationById = useMemo(() => {
        const map = new Map<string, Citation>();
        data?.citations.forEach((c) => map.set(c.citation_id, c));
        return map;
    }, [data]);

    const clauseIndexById = useMemo(() => new Map(
        data?.clauses.map((clause, index) => [clause.clause_id, index] as const) ?? []
    ), [data]);

    // Danh sách rủi ro sắp xếp theo start_char của clause tương ứng (khớp ReportModel)
    const sortedRisks = useMemo(() => {
        if (!data) return [];
        const clauseOrder = new Map<string, number>();
        data.clauses.forEach((c) => clauseOrder.set(c.clause_id, c.start_char));
        return [...data.risks].sort((a, b) => {
            const startA = clauseOrder.get(a.clause_id) ?? 0;
            const startB = clauseOrder.get(b.clause_id) ?? 0;
            return startA - startB;
        });
    }, [data]);

    // Dựng các đoạn văn bản từ canonical_text bằng offset code point (INV-12 & TDD §5.9)
    const segments = useMemo(() => {
        if (!data) return [];
        return buildSegments(data.canonical_text, data.clauses, data.risks);
    }, [data]);

    function selectClause(clauseId: string) {
        setActiveClauseId(clauseId);
        cardRefs.current[clauseId]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function selectRelatedClause(clauseId: string) {
        setActiveClauseId(clauseId);
        textRefs.current[clauseId]?.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    async function handleExport() {
        setExporting(true);
        setError(null);
        try {
            const blob = await exportReport(sessionId, "docx");
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `bao-cao-rui-ro-${sessionId.slice(0, 8)}.docx`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            setError(messageFor(err instanceof ApiError ? err.code : null));
        } finally {
            setExporting(false);
        }
    }

    async function handleEndSession() {
        try {
            await endSession(sessionId);
        } catch {
            // ignore
        } finally {
            onReset();
        }
    }

    if (error && !data) {
        // Phân biệt các mã lỗi đặc biệt khi lấy kết quả (TDD §5.8)
        const isNotReady = error === messageFor("SESSION_NOT_READY");
        const isRejected = error === messageFor("SESSION_REJECTED");
        const isExpired = error === messageFor("SESSION_EXPIRED") || error === messageFor("SESSION_NOT_FOUND");
        void isNotReady; void isRejected; void isExpired; // dùng để gợi ý ý nghĩa, UI chung cho cả 3
        return (
            <main className="page">
                <h1>Không tải được kết quả</h1>
                <p className="error">{error}</p>
                <button onClick={onReset}>Mở phiên mới</button>
            </main>
        );
    }

    if (!data) {
        return (
            <main className="page">
                <p className="lead">Đang tải báo cáo kết quả…</p>
            </main>
        );
    }

    return (
        <main className="page-wide">
            <header className="result-header">
                <div>
                    <h1>Báo cáo phân tích rủi ro hợp đồng</h1>
                    <p className="muted">
                        Vai trò: <strong>{data.role === "EMPLOYEE" ? "Người lao động" : "Người sử dụng lao động"}</strong>
                        {" · "}Ngày phân tích: {data.analysis_date}
                        {" · "}Kết quả: <strong>{data.risks.length}</strong> mục phân tích
                    </p>
                </div>
                <div className="actions">
                    <button type="button" onClick={handleExport} disabled={exporting}>
                        {exporting ? "Đang xuất…" : "Xuất báo cáo DOCX"}
                    </button>
                    <button type="button" className="btn-secondary" onClick={handleEndSession}>
                        Kết thúc phiên
                    </button>
                </div>
            </header>

            {error && <p className="error" role="alert">{error}</p>}

            {/* Trường hợp không phát hiện rủi ro (FR-20) */}
            {data.risks.length === 0 && (
                <section className="card no-risk-banner" role="status">
                    <strong>{messageFor("NO_RISK")}</strong>
                </section>
            )}

            <div className="split-view">
                {/* Cột trái: Văn bản hợp đồng chuẩn hóa (FR-19) */}
                <section className="panel" aria-label="Văn bản trích xuất">
                    <div className="panel-head">
                        <h2>Văn bản hợp đồng</h2>
                        <small>Đây là bản văn bản trích xuất chuẩn hóa (canonical text), không phải tệp PDF/DOCX gốc.</small>
                    </div>
                    <div className="canonical-box">
                        {segments.map((seg) => {
                            if (!seg.clauseId) {
                                return <span key={seg.key}>{seg.text}</span>;
                            }
                            if (!seg.risk) {
                                return <span key={seg.key} ref={(el) => { textRefs.current[seg.clauseId!] = el; }}>{seg.text}</span>;
                            }
                            const view = classifyRisk(seg.risk);
                            const sevClass = view === "NEEDS_REVIEW" ? "hl-review"
                                : view === "INSUFFICIENT" ? "hl-insufficient"
                                    : `hl-${seg.risk.severity?.toLowerCase()}`;
                            const isSelected = activeClauseId === seg.clauseId;
                            return (
                                <mark
                                    key={seg.key}
                                    ref={(el) => { textRefs.current[seg.clauseId!] = el; }}
                                    className={`hl ${sevClass}${isSelected ? " hl-active" : ""}`}
                                    onClick={() => selectClause(seg.clauseId!)}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && selectClause(seg.clauseId!)}
                                >
                                    {seg.text}
                                </mark>
                            );
                        })}
                    </div>
                </section>

                {/* Cột phải: Chi tiết từng điều khoản rủi ro */}
                <section className="panel" aria-label="Chi tiết rủi ro">
                    <div className="panel-head">
                        <h2>Chi tiết rủi ro ({data.risks.length})</h2>
                        <small>Bấm vào đoạn tô màu bên trái để xem chi tiết căn cứ pháp lý tương ứng.</small>
                    </div>
                    <div className="risk-list">
                        {sortedRisks.map((risk) => {
                            const clause = data.clauses.find((c) => c.clause_id === risk.clause_id);
                            const clauseIndex = clauseIndexById.get(risk.clause_id) ?? 0;
                            const isSelected = activeClauseId === risk.clause_id;
                            const view = classifyRisk(risk);
                            const related = (risk.related_clause_ids ?? []).flatMap((id) => {
                                const index = clauseIndexById.get(id);
                                return index === undefined ? [] : [{ id, clause: data.clauses[index], index }];
                            });

                            return (
                                <article
                                    key={risk.clause_id}
                                    ref={(el) => { cardRefs.current[risk.clause_id] = el; }}
                                    className={`risk-card${view === "NEEDS_REVIEW" ? " risk-card-review" : ""}${isSelected ? " risk-card-active" : ""}`}
                                    onClick={() => setActiveClauseId(risk.clause_id)}
                                >
                                    <header className="risk-card-head">
                                        <span className="clause-tag">
                                            {view === "NEEDS_REVIEW" ? "Nghi ngờ, cần xem xét" : clause ? clauseLabel(clause, clauseIndex) : "Điều khoản chưa xác định"}
                                            {view === "NEEDS_REVIEW" && clause && <small>{clauseLabel(clause, clauseIndex)}</small>}
                                        </span>
                                        {view === "SUPPORTED" && (
                                            <span className={`badge badge-${risk.severity!.toLowerCase()}`}>
                                                Mức độ: {labelName(risk.severity!)}
                                            </span>
                                        )}
                                    </header>

                                    {/* Hiển thị tất cả nhãn rủi ro + basis_type của điều khoản đó (TDD §5.9) */}
                                    {view !== "NEEDS_REVIEW" && <div className="basis-tags">
                                        {risk.risk_basis.map((b) => (
                                            <span key={b.label} className="basis-pill">
                                                <strong>{labelName(b.label)}</strong> · {labelName(b.basis_type)}
                                            </span>
                                        ))}
                                    </div>}

                                    {clause && (
                                        <blockquote className="clause-quote">{clause.original_text.trim()}</blockquote>
                                    )}

                                    {view === "NEEDS_REVIEW" && <p className="explanation">{REVIEW_MESSAGE}</p>}
                                    {view === "INSUFFICIENT" && <p className="explanation">{INSUFFICIENT_MESSAGE}</p>}
                                    {(view !== "NEEDS_REVIEW" || risk.explanation.trim() !== `${REVIEW_MESSAGE}.`) &&
                                        <p className="explanation">{risk.explanation}</p>}

                                    {related.length > 0 && (
                                        <p className="related-clauses">Liên quan: {related.map(({ id, clause: relatedClause, index }, position) => (
                                            <span key={id}>
                                                {position > 0 ? ", " : ""}
                                                <button type="button" className="related-link" onClick={(event) => {
                                                    event.stopPropagation();
                                                    selectRelatedClause(id);
                                                }}>{clauseLabel(relatedClause, index)}</button>
                                            </span>
                                        ))}</p>
                                    )}

                                    {risk.citation_ids.length > 0 && (
                                        <div className="citations">
                                            <strong>Căn cứ pháp lý:</strong>
                                            <ul>
                                                {risk.citation_ids.map((cid) => {
                                                    const cit = citationById.get(cid);
                                                    return (
                                                        <li key={cid}>
                                                            <strong>{cit ? `${cit.document_name} (Điều ${cit.article}${cit.clause ? `, Khoản ${cit.clause}` : ""})` : cid}:</strong>{" "}
                                                            {cit?.content}
                                                        </li>
                                                    );
                                                })}
                                            </ul>
                                        </div>
                                    )}
                                </article>
                            );
                        })}
                    </div>
                </section>
            </div>

            <aside className="notices" aria-label="Lưu ý pháp lý và dữ liệu">
                <p><strong>Lưu ý.</strong> {data.disclaimer || DISCLAIMER}</p>
                <p><strong>Dữ liệu của bạn.</strong> {data.data_notice || DATA_NOTICE}</p>
            </aside>
        </main>
    );
}

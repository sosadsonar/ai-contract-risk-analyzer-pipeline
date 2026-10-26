import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, endSession, exportReport, getResult } from "../api/client";
import type { Citation, FinalResult, RiskResult } from "../api/types";
import { labelName } from "../lib/labels";
import { messageFor } from "../lib/messages";
import { DATA_NOTICE, DISCLAIMER } from "../lib/notices";
import { buildCodePointIndex, cpLength, cpSlice } from "../lib/offset";

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

    const riskByClause = useMemo(() => {
        const map = new Map<string, RiskResult>();
        data?.risks.forEach((r) => map.set(r.clause_id, r));
        return map;
    }, [data]);

    const citationById = useMemo(() => {
        const map = new Map<string, Citation>();
        data?.citations.forEach((c) => map.set(c.citation_id, c));
        return map;
    }, [data]);

    // Dựng các đoạn văn bản từ canonical_text bằng offset code point (INV-12)
    const segments = useMemo(() => {
        if (!data) return [];
        const text = data.canonical_text;
        const idx = buildCodePointIndex(text);
        const totalCp = cpLength(idx);
        const sorted = [...data.clauses].sort((a, b) => a.start_char - b.start_char);
        const out: { key: string; text: string; clauseId?: string; risk?: RiskResult }[] = [];
        let cursor = 0;

        for (const c of sorted) {
            if (c.start_char > cursor) {
                out.push({ key: `plain_${cursor}`, text: cpSlice(text, cursor, c.start_char, idx) });
            }
            out.push({
                key: c.clause_id,
                text: cpSlice(text, c.start_char, c.end_char, idx),
                clauseId: c.clause_id,
                risk: riskByClause.get(c.clause_id),
            });
            cursor = c.end_char;
        }
        if (cursor < totalCp) {
            out.push({ key: `tail_${cursor}`, text: cpSlice(text, cursor, totalCp, idx) });
        }
        return out;
    }, [data, riskByClause]);

    function selectClause(clauseId: string) {
        setActiveClauseId(clauseId);
        cardRefs.current[clauseId]?.scrollIntoView({ behavior: "smooth", block: "nearest" });
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
                        {" · "}Phát hiện: <strong>{data.risks.length}</strong> điều khoản có rủi ro
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
                            if (!seg.risk || !seg.clauseId) {
                                return <span key={seg.key}>{seg.text}</span>;
                            }
                            const sevClass = seg.risk.evidence_status === "INSUFFICIENT_EVIDENCE" || !seg.risk.severity
                                ? "hl-insufficient"
                                : `hl-${seg.risk.severity.toLowerCase()}`;
                            const isSelected = activeClauseId === seg.clauseId;
                            return (
                                <mark
                                    key={seg.key}
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
                        {data.risks.map((risk) => {
                            const clause = data.clauses.find((c) => c.clause_id === risk.clause_id);
                            const isSelected = activeClauseId === risk.clause_id;
                            const isInsufficient = risk.evidence_status === "INSUFFICIENT_EVIDENCE" || risk.severity === null;

                            return (
                                <article
                                    key={risk.clause_id}
                                    ref={(el) => { cardRefs.current[risk.clause_id] = el; }}
                                    className={`risk-card${isSelected ? " risk-card-active" : ""}`}
                                    onClick={() => setActiveClauseId(risk.clause_id)}
                                >
                                    <header className="risk-card-head">
                                        <span className="clause-tag">Điều khoản {risk.clause_id}</span>
                                        {/* FR-18 / DEC-12: INSUFFICIENT_EVIDENCE không hiện badge severity */}
                                        {isInsufficient ? (
                                            <span className="badge badge-insufficient">{messageFor("INSUFFICIENT_EVIDENCE")}</span>
                                        ) : (
                                            <span className={`badge badge-${risk.severity!.toLowerCase()}`}>
                                                Mức độ: {labelName(risk.severity!)}
                                            </span>
                                        )}
                                    </header>

                                    {/* Hiển thị tất cả nhãn rủi ro + basis_type của điều khoản đó (TDD §5.9) */}
                                    <div className="basis-tags">
                                        {risk.risk_basis.map((b) => (
                                            <span key={b.label} className="basis-pill">
                                                <strong>{labelName(b.label)}</strong> · {labelName(b.basis_type)}
                                            </span>
                                        ))}
                                    </div>

                                    {clause && (
                                        <blockquote className="clause-quote">{clause.original_text.trim()}</blockquote>
                                    )}

                                    <p className="explanation">{risk.explanation}</p>

                                    {risk.citation_ids.length > 0 && (
                                        <div className="citations">
                                            <strong>Căn cứ pháp lý:</strong>
                                            <ul>
                                                {risk.citation_ids.map((cid) => {
                                                    const cit = citationById.get(cid);
                                                    return (
                                                        <li key={cid}>
                                                            <strong>{cit ? `${cit.document_name} (Điều ${cit.article})` : cid}:</strong>{" "}
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
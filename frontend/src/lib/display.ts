// X-23: hiển thị số Điều thay cho clause_id kỹ thuật (cl_xxxx), cùng quy tắc với backend
// `app.result.report_model.clause_display`: clause mở đầu bằng "Điều N" ⇒ "Điều N"; còn lại
// "Điều khoản số <thứ tự trong văn bản>".
import type { Citation, Clause } from "../api/types";

const ARTICLE = /^\s*Điều\s+(\d+[a-zA-ZđĐ]?)/i;

export function clauseDisplayMap(clauses: Clause[]): Map<string, string> {
  const ordered = [...clauses].sort((a, b) => a.start_char - b.start_char);
  const out = new Map<string, string>();
  ordered.forEach((c, i) => {
    const m = ARTICLE.exec(c.original_text);
    out.set(c.clause_id, m ? `Điều ${m[1]}` : `Điều khoản số ${i + 1}`);
  });
  return out;
}

/** "Liên quan: Điều 3, Điều 5" (FR-32); rỗng nếu không có related_clause_ids. */
export function relatedLine(ids: string[] | undefined, display: Map<string, string>): string {
  if (!ids || ids.length === 0) return "";
  return "Liên quan: " + ids.map((id) => display.get(id) ?? id).join(", ");
}

/** "Khoản 1 Điều 21 Bộ luật Lao động 2019" — thẻ citation hiện nguyên văn Khoản ở thân (X-23). */
export function citationHeading(c: Citation): string {
  const parts: string[] = [];
  if (c.clause) parts.push(`Khoản ${c.clause}`);
  if (c.article) parts.push(`Điều ${c.article}`);
  if (c.document_name) parts.push(c.document_name);
  return parts.join(" ") || c.citation_id;
}

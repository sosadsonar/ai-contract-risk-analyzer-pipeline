// Dựng các đoạn văn bản hiển thị từ canonical_text, clauses và risks
// Tuân thủ INV-12 (Unicode code point offset) và TDD §5.9 (1 highlight / 1 clause).
import type { Clause, RiskResult } from "../api/types";
import { buildCodePointIndex, cpLength, cpSlice } from "./offset";

export interface TextSegment {
  key: string;
  text: string;
  clauseId?: string;
  risk?: RiskResult;
}

/**
 * Chia canonical_text thành danh sách các segment liên tục phủ toàn bộ văn bản:
 * - Khoảng trống giữa các clause (tiêu đề, khoảng trắng) là plain segment (không clauseId, không risk).
 * - Mỗi clause là đúng MỘT segment (dù clause có 1 hay nhiều risk_labels - TDD §5.9).
 * - Nếu clause có trong risks -> gắn risk vào segment (được tô highlight).
 * - Nếu clause KHÔNG có trong risks -> risk = undefined (không tô highlight).
 * - Invariant: Nối text của mọi segment lại phải bằng đúng canonicalText.
 */
export function buildSegments(
  canonicalText: string,
  clauses: Clause[],
  risks: RiskResult[],
): TextSegment[] {
  if (!canonicalText) return [];

  const riskByClause = new Map<string, RiskResult>();
  for (const r of risks) {
    // TDD §5.9: 1 highlight cho mỗi clause; nếu có nhiều risk record cùng clause_id thì giữ record đại diện
    if (!riskByClause.has(r.clause_id)) {
      riskByClause.set(r.clause_id, r);
    }
  }

  const idx = buildCodePointIndex(canonicalText);
  const totalCp = cpLength(idx);
  const sorted = [...clauses].sort((a, b) => a.start_char - b.start_char);
  const out: TextSegment[] = [];
  let cursor = 0;

  for (const c of sorted) {
    if (c.start_char > cursor) {
      out.push({
        key: `plain_${cursor}`,
        text: cpSlice(canonicalText, cursor, c.start_char, idx),
      });
    }
    out.push({
      key: c.clause_id,
      text: cpSlice(canonicalText, c.start_char, c.end_char, idx),
      clauseId: c.clause_id,
      risk: riskByClause.get(c.clause_id),
    });
    cursor = c.end_char;
  }

  if (cursor < totalCp) {
    out.push({
      key: `tail_${cursor}`,
      text: cpSlice(canonicalText, cursor, totalCp, idx),
    });
  }

  return out;
}


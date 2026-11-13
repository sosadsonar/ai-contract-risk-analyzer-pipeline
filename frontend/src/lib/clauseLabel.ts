import type { Clause } from "../api/types";

export function clauseLabel(clause: Clause, index: number): string {
  // final_result_v1 chưa có clause_number; mock có thể cung cấp tạm.
  const raw = "clause_number" in clause ? clause.clause_number : undefined;
  const number = typeof raw === "string" ? raw.trim() : "";
  if (!number) return `Điều khoản thứ ${index + 1}`;
  return /^\d+$/.test(number) ? `Điều ${number}` : `Mục ${number}`;
}

import type { RiskResult } from "../api/types";

export type RiskView = "NEEDS_REVIEW" | "INSUFFICIENT" | "SUPPORTED";

export function classifyRisk(risk: RiskResult): RiskView {
  // NEEDS_REVIEW là quy ước mock tạm; final_result_v1 chưa cho phép risk_labels rỗng.
  if (risk.risk_labels.length === 0 && risk.severity === null) return "NEEDS_REVIEW";
  if (risk.evidence_status === "INSUFFICIENT_EVIDENCE" || risk.severity === null) return "INSUFFICIENT";
  return "SUPPORTED";
}

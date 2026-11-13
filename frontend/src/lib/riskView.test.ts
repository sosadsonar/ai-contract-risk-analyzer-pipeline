import { describe, expect, it } from "vitest";
import type { RiskResult } from "../api/types";
import { classifyRisk } from "./riskView";

const supported: RiskResult = {
  clause_id: "cl_0001", risk_labels: ["PROBATION"],
  risk_basis: [{ label: "PROBATION", basis_type: "LEGAL_VIOLATION" }],
  severity: "HIGH", explanation: "Giải thích rủi ro", evidence_status: "SUPPORTED",
  citation_ids: ["BLLD2019:art26"],
};

describe("classifyRisk", () => {
  it("bản ghi không nhãn, không severity cần xem xét", () => {
    expect(classifyRisk({ ...supported, risk_labels: [], risk_basis: [], severity: null,
      evidence_status: "INSUFFICIENT_EVIDENCE", citation_ids: [] })).toBe("NEEDS_REVIEW");
  });

  it("có nhãn nhưng thiếu căn cứ hoặc severity là INSUFFICIENT", () => {
    expect(classifyRisk({ ...supported, severity: null })).toBe("INSUFFICIENT");
    expect(classifyRisk({ ...supported, evidence_status: "INSUFFICIENT_EVIDENCE" })).toBe("INSUFFICIENT");
  });

  it("còn lại SUPPORTED và được phép hiện severity", () => {
    expect(classifyRisk(supported)).toBe("SUPPORTED");
  });
});

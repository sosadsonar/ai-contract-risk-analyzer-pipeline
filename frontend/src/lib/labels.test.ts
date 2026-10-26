import { describe, expect, it } from "vitest";
import { BASIS_TYPE_NAMES, CLAUSE_LABEL_NAMES, RISK_LABEL_NAMES, labelName } from "./labels";

describe("labels", () => {
  it("đủ số nhãn theo taxonomy hiện tại (21 rủi ro, 12 clause, 3 basis_type)", () => {
    expect(Object.keys(RISK_LABEL_NAMES)).toHaveLength(21);
    expect(Object.keys(CLAUSE_LABEL_NAMES)).toHaveLength(12);
    expect(Object.keys(BASIS_TYPE_NAMES)).toHaveLength(3);
  });
  it("mã lạ không làm vỡ UI", () => {
    expect(labelName("NEW_LABEL")).toBe("NEW_LABEL");
    expect(labelName("PROBATION")).toBe("Thử việc");
  });
});

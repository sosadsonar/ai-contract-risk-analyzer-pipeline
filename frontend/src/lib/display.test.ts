import { describe, expect, it } from "vitest";
import type { Citation, Clause } from "../api/types";
import { citationHeading, clauseDisplayMap, relatedLine } from "./display";

const clauses: Clause[] = [
  { clause_id: "cl_0002", original_text: "Điều 3. Tiền lương", start_char: 20, end_char: 38, clause_labels: ["OTHER"] },
  { clause_id: "cl_0001", original_text: "HỢP ĐỒNG LAO ĐỘNG", start_char: 0, end_char: 17, clause_labels: ["OTHER"] },
  { clause_id: "cl_0003", original_text: "1. Lương chính", start_char: 40, end_char: 54, clause_labels: ["OTHER"] },
];

describe("display (X-23)", () => {
  it("dùng số Điều khi clause mở đầu bằng heading, còn lại dùng thứ tự", () => {
    const m = clauseDisplayMap(clauses);
    expect(m.get("cl_0002")).toBe("Điều 3");
    expect(m.get("cl_0001")).toBe("Điều khoản số 1");
    expect(m.get("cl_0003")).toBe("Điều khoản số 3");
  });

  it("dòng Liên quan", () => {
    const m = clauseDisplayMap(clauses);
    expect(relatedLine(["cl_0002"], m)).toBe("Liên quan: Điều 3");
    expect(relatedLine(undefined, m)).toBe("");
  });

  it("tiêu đề citation có Khoản khi nút là Khoản", () => {
    const c: Citation = { citation_id: "X", document_name: "Bộ luật Lao động 2019", article: "21", content: "…", clause: "1" };
    expect(citationHeading(c)).toBe("Khoản 1 Điều 21 Bộ luật Lao động 2019");
    expect(citationHeading({ ...c, clause: undefined })).toBe("Điều 21 Bộ luật Lao động 2019");
  });
});

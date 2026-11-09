import { describe, expect, it } from "vitest";
import type { Stage } from "../api/types";
import { getStageName, STAGE_NAMES } from "./stages";

const ALL_12_STAGES: Stage[] = [
  "UPLOAD",
  "EXTRACTION",
  "SCOPE_PRECHECK",
  "PII_MASKING",
  "SEGMENTATION",
  "CLAUSE_GRAPH",
  "CLAUSE_CLASSIFICATION",
  "LEGAL_RETRIEVAL",
  "RISK_ANALYSIS",
  "CITATION_VALIDATION",
  "ASSEMBLY",
  "EXPORT",
];

describe("stages (TDD §5.3, §5.9)", () => {
  it("đủ 12 stage theo schema và đều có tên hiển thị tiếng Việt", () => {
    expect(Object.keys(STAGE_NAMES)).toHaveLength(12);

    for (const stage of ALL_12_STAGES) {
      const name = getStageName(stage);
      expect(name, `Thiếu tên tiếng Việt cho stage ${stage}`).toBeTruthy();
      // Phải có chữ tiếng Việt
      expect(name).toMatch(/[a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]/i);
      // Không được trả về chính mã kỹ thuật thô
      expect(name).not.toBe(stage);
    }
  });

  it("stage lạ trả về câu chung tiếng Việt, KHÔNG chứa mã kỹ thuật thô", () => {
    const strangeStage = "UNKNOWN_NEW_AI_STAGE_V9";
    const name = getStageName(strangeStage);

    expect(name).toBe("Đang xử lý…");
    expect(name).not.toContain(strangeStage);
    expect(name).not.toContain("Giai đoạn:");
  });

  it("null/undefined/rỗng trả về 'Khởi tạo phiên'", () => {
    expect(getStageName(null)).toBe("Khởi tạo phiên");
    expect(getStageName(undefined)).toBe("Khởi tạo phiên");
    expect(getStageName("")).toBe("Khởi tạo phiên");
  });
});


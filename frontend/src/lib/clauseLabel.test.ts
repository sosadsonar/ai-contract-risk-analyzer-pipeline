import { describe, expect, it } from "vitest";
import type { Clause } from "../api/types";
import { clauseLabel } from "./clauseLabel";

const base: Clause = {
  clause_id: "cl_0001", original_text: "Điều khoản mẫu", start_char: 0,
  end_char: 14, clause_labels: ["OTHER"],
};

describe("clauseLabel", () => {
  it("số nguyên thuần hiện Điều", () => {
    const clause = { ...base, clause_number: "7" };
    expect(clauseLabel(clause, 0)).toBe("Điều 7");
  });

  it("số dạng khác hiện Mục", () => {
    const clause = { ...base, clause_number: "7.2" };
    expect(clauseLabel(clause, 0)).toBe("Mục 7.2");
  });

  it("không có số thì dùng thứ tự, không lộ clause_id", () => {
    expect(clauseLabel(base, 2)).toBe("Điều khoản thứ 3");
    const empty = { ...base, clause_number: "" };
    const missing = { ...base, clause_number: null };
    expect(clauseLabel(empty, 1)).toBe("Điều khoản thứ 2");
    expect(clauseLabel(missing, 0)).toBe("Điều khoản thứ 1");
  });
});

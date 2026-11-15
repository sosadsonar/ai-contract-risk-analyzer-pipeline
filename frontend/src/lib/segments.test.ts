// @ts-ignore fs is available in Vitest node test environment
import fs from "node:fs";
// @ts-ignore path is available in Vitest node test environment
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { Clause, FinalResult, RiskResult } from "../api/types";
import { buildSegments } from "./segments";

declare const process: any;

describe("buildSegments (INV-12 & TDD §5.9)", () => {
  it("(a) ghép toàn bộ text của các đoạn phải bằng đúng canonical_text", () => {
    const text = "Mở đầu hợp đồng.\nĐiều 1. Lương 10 triệu.\nĐiều 2. Thời gian làm việc 8h.\nPhần kết.";
    const clauses: Clause[] = [
      {
        clause_id: "cl_1",
        original_text: "Điều 1. Lương 10 triệu.\n",
        start_char: 17,
        end_char: 41,
        clause_labels: ["COMPENSATION_BENEFITS"],
      },
      {
        clause_id: "cl_2",
        original_text: "Điều 2. Thời gian làm việc 8h.\n",
        start_char: 41,
        end_char: 72,
        clause_labels: ["WORKING_TIME"],
      },
    ];
    const risks: RiskResult[] = [
      {
        clause_id: "cl_1",
        risk_labels: ["WAGE_AMOUNT_COMPONENTS"],
        risk_basis: [{ label: "WAGE_AMOUNT_COMPONENTS", basis_type: "UNFAVORABLE" }],
        severity: "LOW",
        explanation: "Lương chưa chi tiết",
        evidence_status: "SUPPORTED",
        citation_ids: [],
      },
    ];

    const segments = buildSegments(text, clauses, risks);
    const joined = segments.map((s) => s.text).join("");
    expect(joined).toBe(text);
  });

  it("(b) có ký tự ngoài BMP (📄, 😀) vẫn tính đúng offset code point", () => {
    // 😀 và 📄 chiếm 2 code units trong UTF-16 nhưng là 1 Unicode code point
    const preamble = "Tiêu đề 📄\n";
    const clauseText = "Điều 1. Thử việc 😀 90 ngày.\n";
    const tail = "Kết thúc.";
    const text = preamble + clauseText + tail;

    const start_char = Array.from(preamble).length;
    const end_char = start_char + Array.from(clauseText).length;

    const clauses: Clause[] = [
      {
        clause_id: "cl_emoji",
        original_text: clauseText,
        start_char,
        end_char,
        clause_labels: ["PROBATION"],
      },
    ];
    const risks: RiskResult[] = [
      {
        clause_id: "cl_emoji",
        risk_labels: ["PROBATION"],
        risk_basis: [{ label: "PROBATION", basis_type: "LEGAL_VIOLATION" }],
        severity: "HIGH",
        explanation: "Thử việc sai luật",
        evidence_status: "SUPPORTED",
        citation_ids: [],
      },
    ];

    const segments = buildSegments(text, clauses, risks);
    expect(segments.map((s) => s.text).join("")).toBe(text);

    const targetSeg = segments.find((s) => s.clauseId === "cl_emoji");
    expect(targetSeg).toBeDefined();
    expect(targetSeg!.text).toBe(clauseText);
    expect(targetSeg!.risk).toBeDefined();
  });

  it("(c) clause không có risk thì segment.risk = undefined (không được tô)", () => {
    const text = "Điều 1. Có rủi ro.\nĐiều 2. Không có rủi ro.";
    const clauses: Clause[] = [
      {
        clause_id: "cl_1",
        original_text: "Điều 1. Có rủi ro.\n",
        start_char: 0,
        end_char: 19,
        clause_labels: ["PROBATION"],
      },
      {
        clause_id: "cl_2",
        original_text: "Điều 2. Không có rủi ro.",
        start_char: 19,
        end_char: 43,
        clause_labels: ["WORKING_TIME"],
      },
    ];
    const risks: RiskResult[] = [
      {
        clause_id: "cl_1",
        risk_labels: ["PROBATION"],
        risk_basis: [{ label: "PROBATION", basis_type: "LEGAL_VIOLATION" }],
        severity: "HIGH",
        explanation: "Có rủi ro",
        evidence_status: "SUPPORTED",
        citation_ids: [],
      },
    ];

    const segments = buildSegments(text, clauses, risks);
    const seg1 = segments.find((s) => s.clauseId === "cl_1");
    const seg2 = segments.find((s) => s.clauseId === "cl_2");

    expect(seg1?.risk).toBeDefined();
    expect(seg2?.risk).toBeUndefined();
  });

  it("(d) clause có nhiều risk_labels chỉ tạo đúng MỘT highlight segment (TDD §5.9)", () => {
    const text = "Điều 3. Vừa cam kết đào tạo vừa hạn chế làm việc.";
    const clauses: Clause[] = [
      {
        clause_id: "cl_3",
        original_text: text,
        start_char: 0,
        end_char: text.length,
        clause_labels: ["TRAINING", "EMPLOYEE_OBLIGATIONS_DISCIPLINE"],
      },
    ];
    const risks: RiskResult[] = [
      {
        clause_id: "cl_3",
        risk_labels: ["TRAINING_COMMITMENT", "POST_EMPLOYMENT_RESTRICTION"],
        risk_basis: [
          { label: "TRAINING_COMMITMENT", basis_type: "UNFAVORABLE" },
          { label: "POST_EMPLOYMENT_RESTRICTION", basis_type: "UNFAVORABLE" },
        ],
        severity: "MEDIUM",
        explanation: "Hai nhãn rủi ro trên cùng một điều khoản",
        evidence_status: "SUPPORTED",
        citation_ids: [],
      },
    ];

    const segments = buildSegments(text, clauses, risks);
    const clauseSegments = segments.filter((s) => s.clauseId === "cl_3");
    // Chỉ có đúng 1 segment đại diện cho clause, không bị phân tách hay nhân đôi
    expect(clauseSegments).toHaveLength(1);
    expect(clauseSegments[0].risk?.risk_labels).toHaveLength(2);
  });

  it("(e) đọc fixture backend/app/session/fixtures/mock_final_result_v1.json và kiểm partition khớp", () => {
    // Đọc fixture bằng fs với đường dẫn tương đối từ frontend/
    const fixturePath = path.resolve(process.cwd(), "../backend/app/session/fixtures/mock_final_result_v1.json");
    expect(fs.existsSync(fixturePath), `Không tìm thấy file: ${fixturePath}`).toBe(true);

    const raw = fs.readFileSync(fixturePath, "utf-8");
    const result = JSON.parse(raw) as FinalResult;

    const segments = buildSegments(result.canonical_text, result.clauses, result.risks);

    // Ghép lại toàn văn khớp canonical_text
    expect(segments.map((s) => s.text).join("")).toBe(result.canonical_text);

    // cl_0001 có risk
    const seg1 = segments.find((s) => s.clauseId === "cl_0001");
    expect(seg1).toBeDefined();
    expect(seg1?.risk).toBeDefined();
    expect(seg1?.risk?.risk_labels).toContain("DEPOSIT_DOCUMENT_HELD");

    // cl_0002 không có risk
    const seg2 = segments.find((s) => s.clauseId === "cl_0002");
    expect(seg2).toBeDefined();
    expect(seg2?.risk).toBeUndefined();

    // Văn bản có ký tự non-BMP 📄 ở cl_0002
    expect(seg2?.text).toContain("📄");
  });
});

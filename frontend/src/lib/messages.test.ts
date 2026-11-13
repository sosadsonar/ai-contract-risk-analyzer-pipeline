/**
 * Kiểm tra catalog thông báo messages.ts (Việc 3, N5 tuần 3–4).
 * Đảm bảo mọi error_code trong backend/app/api/errors.py MESSAGES đều có
 * thông báo tiếng Việt đầy đủ ở frontend và không hiện mã kỹ thuật một mình.
 */
import { describe, expect, it } from "vitest";
import { messageFor, MESSAGES } from "./messages";
// @ts-ignore fs is available in the Vitest node environment
import fs from "node:fs";
// @ts-ignore path is available in the Vitest node environment
import path from "node:path";

declare const process: { cwd(): string };

// Tất cả code trong backend/app/api/errors.py MESSAGES (14 mục, cập nhật khi backend thêm code mới).
const BACKEND_ERROR_CODES = [
  "ROLE_REQUIRED",
  "SESSION_NOT_FOUND",
  "SESSION_EXPIRED",
  "SESSION_NOT_READY",
  "SESSION_REJECTED",
  "INVALID_SESSION_STATE",
  "RETRY_LIMIT_EXCEEDED",
  "FEATURE_NOT_ENABLED",
  "UNSUPPORTED_FILE_TYPE",
  "FILE_TOO_LARGE",
  "SYSTEM_BUSY",
  "RATE_LIMITED",
  "QUOTA_EXCEEDED",
  "INTERNAL_ERROR",
] as const;

// Tất cả code trong TDD Phụ lục E (catalog thông báo UI tối thiểu)
const APPENDIX_E_CODES = [
  "SYSTEM_BUSY",
  "QUOTA_EXCEEDED",
  "RATE_LIMITED",
  "UNSUPPORTED_FILE_TYPE",
  "FILE_TOO_LARGE",
  "PDF_PAGE_LIMIT_EXCEEDED",
  "DOCX_TEXT_LIMIT_EXCEEDED",
  "NO_EXTRACTABLE_TEXT",
  "UNSUPPORTED_TEXT_ENCODING",
  "NOT_LABOR_CONTRACT",
  "TOO_MANY_CLAUSES",
  "AI_TIMEOUT",
  "AI_PROVIDER_ERROR",
  "AI_OUTPUT_INVALID",
  "REJECTED",
  "INSUFFICIENT_EVIDENCE",
  "NO_RISK",
  "EXPIRED",
] as const;

// Mã bổ sung từ SRS §6.2 và client
const SRS_EXTRA_CODES = [
  "ROLE_REQUIRED",
  "NETWORK_ERROR",
  "RETRY_LIMIT_EXCEEDED",
  "INVALID_SESSION_STATE",
  "SESSION_NOT_READY",
  "SESSION_REJECTED",
  "SESSION_EXPIRED",
  "SESSION_NOT_FOUND",
  "FEATURE_NOT_ENABLED",
  "INTERNAL_ERROR",
] as const;

const ALL_CODES = Array.from(new Set([
  ...BACKEND_ERROR_CODES,
  ...APPENDIX_E_CODES,
  ...SRS_EXTRA_CODES,
]));

describe("messageFor — catalog đầy đủ (Việc 3)", () => {
  it("mọi error_code của backend đều có thông báo tiếng Việt", () => {
    for (const code of BACKEND_ERROR_CODES) {
      const msg = messageFor(code);
      expect(msg, `Thiếu thông báo cho code: ${code}`).not.toBe(
        "Đã có lỗi xảy ra. Vui lòng thử lại."
      );
      expect(msg.length, `Thông báo rỗng cho: ${code}`).toBeGreaterThan(0);
    }
  });

  it("mọi mã Phụ lục E đều có thông báo tiếng Việt (không dùng thông báo mặc định)", () => {
    for (const code of APPENDIX_E_CODES) {
      const msg = messageFor(code);
      expect(msg, `Thiếu thông báo Phụ lục E cho code: ${code}`).not.toBe(
        "Đã có lỗi xảy ra. Vui lòng thử lại."
      );
      expect(msg.length, `Thông báo rỗng cho Phụ lục E: ${code}`).toBeGreaterThan(0);
    }
  });

  it("không hiện mã kỹ thuật một mình (thông báo phải có ít nhất 1 chữ tiếng Việt)", () => {
    for (const code of ALL_CODES) {
      const msg = messageFor(code);
      // Thông báo phải chứa ít nhất 1 ký tự tiếng Việt (a–z, có dấu, hoặc khoảng trắng)
      expect(msg, `Thông báo cho ${code} trông như mã kỹ thuật: "${msg}"`).toMatch(
        /[a-záàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ]/i
      );
    }
  });

  it("null/undefined trả thông báo mặc định thân thiện", () => {
    expect(messageFor(null)).toBe("Đã có lỗi xảy ra. Vui lòng thử lại.");
    expect(messageFor(undefined)).toBe("Đã có lỗi xảy ra. Vui lòng thử lại.");
    expect(messageFor("UNKNOWN_FUTURE_CODE")).toBe(
      "Đã có lỗi xảy ra. Vui lòng thử lại."
    );
  });

  it("INTERNAL_ERROR có thông báo", () => {
    expect(messageFor("INTERNAL_ERROR")).toBeTruthy();
  });

  it("RETRY_LIMIT_EXCEEDED có thông báo nói đến số lần", () => {
    const msg = messageFor("RETRY_LIMIT_EXCEEDED");
    expect(msg).toMatch(/lần/i);
  });

  it("SESSION_NOT_FOUND có thông báo", () => {
    expect(messageFor("SESSION_NOT_FOUND")).toBeTruthy();
  });

  it("SESSION_EXPIRED có thông báo nói đến hết hạn / xóa", () => {
    const msg = messageFor("SESSION_EXPIRED");
    expect(msg).toMatch(/hết hạn|xóa|kết thúc/i);
  });

  it("FEATURE_NOT_ENABLED có thông báo", () => {
    const msg = messageFor("FEATURE_NOT_ENABLED");
    expect(msg).toBeTruthy();
  });

  it("PDF_PAGE_LIMIT_EXCEEDED có thông báo nói đến trang hoặc trang", () => {
    expect(messageFor("PDF_PAGE_LIMIT_EXCEEDED")).toMatch(/trang|PDF/i);
  });

  it("DOCX_TEXT_LIMIT_EXCEEDED có thông báo nói đến ký tự hoặc DOCX", () => {
    expect(messageFor("DOCX_TEXT_LIMIT_EXCEEDED")).toMatch(/ký tự|DOCX|nội dung/i);
  });

  it("NO_EXTRACTABLE_TEXT có thông báo nói đến trích xuất hoặc scan", () => {
    expect(messageFor("NO_EXTRACTABLE_TEXT")).toMatch(/trích xuất|scan|ảnh/i);
  });

  it("NOT_LABOR_CONTRACT có thông báo nói đến hợp đồng lao động", () => {
    expect(messageFor("NOT_LABOR_CONTRACT")).toMatch(/hợp đồng lao động|lao động/i);
  });

  it("AI_TIMEOUT có thông báo nói đến thử lại", () => {
    expect(messageFor("AI_TIMEOUT")).toMatch(/thử lại/i);
  });

  it("INSUFFICIENT_EVIDENCE có thông báo nói đến căn cứ pháp lý", () => {
    expect(messageFor("INSUFFICIENT_EVIDENCE")).toMatch(/căn cứ|pháp lý/i);
  });

  it("NO_RISK đúng nguyên văn TDD §5.9", () => {
    expect(messageFor("NO_RISK")).toBe("Không phát hiện rủi ro trong phạm vi phân tích.");
  });

  it("toàn bộ catalog và chuỗi cố định trong các trang không dùng cụm bị cấm", () => {
    for (const [code, message] of Object.entries(MESSAGES)) {
      expect(message, code).not.toMatch(/an toàn/i);
    }
    expect(messageFor(null)).not.toMatch(/an toàn/i);
    const pages = path.join(process.cwd(), "src", "pages");
    for (const file of fs.readdirSync(pages).filter((name: string) => name.endsWith(".tsx"))) {
      const source = fs.readFileSync(path.join(pages, file), "utf8");
      expect(source, file).not.toMatch(/an toàn/i);
    }
  });

  it("EXPIRED có thông báo nói đến kết thúc hoặc xóa", () => {
    expect(messageFor("EXPIRED")).toMatch(/kết thúc|xóa|hết hạn/i);
  });
});

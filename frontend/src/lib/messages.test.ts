/**
 * Kiểm tra catalog thông báo messages.ts (Việc 3, N5 tuần 3–4).
 * Đảm bảo mọi error_code trong backend/app/api/errors.py MESSAGES đều có
 * thông báo tiếng Việt đầy đủ ở frontend và không hiện mã kỹ thuật một mình.
 */
import { describe, expect, it } from "vitest";
import { messageFor } from "./messages";

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

  it("không hiện mã kỹ thuật một mình (thông báo phải có ít nhất 1 chữ tiếng Việt)", () => {
    for (const code of BACKEND_ERROR_CODES) {
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
});


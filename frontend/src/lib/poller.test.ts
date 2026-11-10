import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { StatusResponse } from "../api/types";
import { createPoller, nextPollDelay } from "./poller";

function makeStatus(status: StatusResponse["status"], stage = "VALIDATING"): StatusResponse {
  return {
    session_id: "test-session",
    status,
    stage: stage as StatusResponse["stage"],
    manual_retry_count: 0,
    progress: null,
    error_code: status === "FAILED" ? "AI_TIMEOUT" : status === "REJECTED" ? "NOT_LABOR_CONTRACT" : null,
    updated_at: new Date().toISOString(),
  };
}

describe("nextPollDelay (TDD §5.9)", () => {
  it("trả về 1500ms khi thời gian dưới 60s", () => {
    expect(nextPollDelay(0)).toBe(1500);
    expect(nextPollDelay(30_000)).toBe(1500);
    expect(nextPollDelay(59_999)).toBe(1500);
  });

  it("trả về 2500ms khi thời gian đạt hoặc vượt 60s", () => {
    expect(nextPollDelay(60_000)).toBe(2500);
    expect(nextPollDelay(120_000)).toBe(2500);
  });
});

describe("createPoller", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("poll lần đầu sau 500 ms (NFR-PERF-02 / TDD §5.9)", async () => {
    const getStatus = vi.fn().mockResolvedValue(makeStatus("VALIDATING"));
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError });

    // Chưa đủ 500ms -> chưa gọi
    await vi.advanceTimersByTimeAsync(499);
    expect(getStatus).toHaveBeenCalledTimes(0);

    // Đến 500ms -> gọi lần 1
    await vi.advanceTimersByTimeAsync(1);
    expect(getStatus).toHaveBeenCalledTimes(1);
    expect(onStatus).toHaveBeenCalledWith(expect.objectContaining({ status: "VALIDATING" }));

    poller.cancel();
  });

  it("trong 60s đầu, chu kỳ poll là 1500 ms", async () => {
    const getStatus = vi.fn().mockResolvedValue(makeStatus("PROCESSING"));
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError });

    // 500ms đầu
    await vi.advanceTimersByTimeAsync(500);
    expect(getStatus).toHaveBeenCalledTimes(1);

    // Sau thêm 1500ms -> lần 2
    await vi.advanceTimersByTimeAsync(1500);
    expect(getStatus).toHaveBeenCalledTimes(2);

    // Sau thêm 1500ms -> lần 3
    await vi.advanceTimersByTimeAsync(1500);
    expect(getStatus).toHaveBeenCalledTimes(3);

    poller.cancel();
  });

  it("sau 60s, chu kỳ poll giảm xuống 2500 ms", async () => {
    let mockNow = 1_000_000;
    const now = () => mockNow;
    const getStatus = vi.fn().mockResolvedValue(makeStatus("PROCESSING"));
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError, now });

    // 500ms đầu
    await vi.advanceTimersByTimeAsync(500);
    expect(getStatus).toHaveBeenCalledTimes(1);

    // Tua thời gian giả lập vượt mốc 60s (60_001 ms)
    mockNow += 60_001;

    // Sau 1500ms nữa (delay của lần trước tính lúc 500ms < 60s)
    await vi.advanceTimersByTimeAsync(1500);
    expect(getStatus).toHaveBeenCalledTimes(2);

    // Tại lần tick thứ 2, elapsed = 60_001 + 1500 > 60s -> delay tiếp theo phải là 2500ms
    await vi.advanceTimersByTimeAsync(2499);
    expect(getStatus).toHaveBeenCalledTimes(2); // chưa đủ 2500ms

    await vi.advanceTimersByTimeAsync(1);
    expect(getStatus).toHaveBeenCalledTimes(3); // đã đủ 2500ms

    poller.cancel();
  });

  it("dừng polling ngay ở mọi trạng thái kết thúc: COMPLETED, FAILED, REJECTED, EXPIRED", async () => {
    const terminalStatuses = ["COMPLETED", "FAILED", "REJECTED", "EXPIRED"] as const;

    for (const termStatus of terminalStatuses) {
      const getStatus = vi.fn().mockResolvedValue(makeStatus(termStatus));
      const onStatus = vi.fn();
      const onError = vi.fn();

      const poller = createPoller({ getStatus, onStatus, onError });

      // Poll lần đầu 500ms -> nhận terminalStatus
      await vi.advanceTimersByTimeAsync(500);
      expect(getStatus).toHaveBeenCalledTimes(1);
      expect(onStatus).toHaveBeenCalledWith(expect.objectContaining({ status: termStatus }));

      // Tua thêm 10 giây -> không có lần gọi nào nữa
      await vi.advanceTimersByTimeAsync(10_000);
      expect(getStatus).toHaveBeenCalledTimes(1);

      poller.cancel();
    }
  });

  it("dừng hẳn khi gặp SESSION_NOT_FOUND", async () => {
    const notFoundError = new ApiError("SESSION_NOT_FOUND", 404);
    const getStatus = vi.fn().mockRejectedValue(notFoundError);
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError });

    // Poll lần đầu sau 500ms gặp SESSION_NOT_FOUND
    await vi.advanceTimersByTimeAsync(500);
    expect(getStatus).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith("SESSION_NOT_FOUND");

    // Tua thêm 10 giây -> KHÔNG được thử lại nữa
    await vi.advanceTimersByTimeAsync(10_000);
    expect(getStatus).toHaveBeenCalledTimes(1);

    poller.cancel();
  });

  it("lỗi mạng tạm thời thì thử lại sau 2500 ms", async () => {
    const networkError = new ApiError("NETWORK_ERROR", 0, true);
    let attempts = 0;
    const getStatus = vi.fn().mockImplementation(async () => {
      attempts++;
      if (attempts === 1) throw networkError;
      return makeStatus("PROCESSING");
    });
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError });

    // Lần 1 sau 500ms: lỗi mạng
    await vi.advanceTimersByTimeAsync(500);
    expect(getStatus).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith("NETWORK_ERROR");

    // Chưa tới 2500ms -> chưa thử lại
    await vi.advanceTimersByTimeAsync(2499);
    expect(getStatus).toHaveBeenCalledTimes(1);

    // Đến 2500ms -> thử lại lần 2
    await vi.advanceTimersByTimeAsync(1);
    expect(getStatus).toHaveBeenCalledTimes(2);
    expect(onStatus).toHaveBeenCalledWith(expect.objectContaining({ status: "PROCESSING" }));

    poller.cancel();
  });

  it("hủy (cancel) thì lập tức không gọi tiếp", async () => {
    const getStatus = vi.fn().mockResolvedValue(makeStatus("VALIDATING"));
    const onStatus = vi.fn();
    const onError = vi.fn();

    const poller = createPoller({ getStatus, onStatus, onError });

    // Hủy trước khi 500ms trôi qua
    await vi.advanceTimersByTimeAsync(200);
    poller.cancel();

    // Tua quá 500ms và cả 10 giây
    await vi.advanceTimersByTimeAsync(10_000);
    expect(getStatus).toHaveBeenCalledTimes(0);
  });
});


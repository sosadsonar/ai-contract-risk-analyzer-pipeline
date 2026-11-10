// Logic polling thuần túy không phụ thuộc React (TDD §5.9 & NFR-PERF-02).
// Phục vụ usePolling và có thể kiểm thử độc lập với fake timers.
import { ApiError } from "../api/client";
import type { SessionStatus, StatusResponse } from "../api/types";

export const TERMINAL_STATUSES: ReadonlySet<SessionStatus> = new Set([
  "COMPLETED",
  "FAILED",
  "REJECTED",
  "EXPIRED",
]);

/**
 * Tính thời gian chờ poll tiếp theo dựa trên thời gian đã trôi qua kể từ khi bắt đầu phiên poll.
 * TDD §5.9: trong VALIDATING/PROCESSING poll mỗi 1.5s; sau 60s giảm xuống 2.5s.
 */
export function nextPollDelay(elapsedMs: number): number {
  return elapsedMs >= 60_000 ? 2500 : 1500;
}

export interface PollerOptions {
  getStatus: () => Promise<StatusResponse>;
  onStatus: (status: StatusResponse) => void;
  onError: (code: string) => void;
  now?: () => number;
  initialDelayMs?: number; // mặc định 500ms
  networkRetryDelayMs?: number; // mặc định 2500ms
}

export interface PollerController {
  cancel: () => void;
}

/**
 * Tạo một chu trình polling.
 * - Poll lần đầu sau initialDelayMs (500ms).
 * - Chu kỳ lặp theo nextPollDelay (1500ms -> 2500ms sau 60s).
 * - Dừng polling khi nhận trạng thái kết thúc (COMPLETED, FAILED, REJECTED, EXPIRED).
 * - Dừng polling vĩnh viễn khi gặp SESSION_NOT_FOUND.
 * - Thử lại sau networkRetryDelayMs (2500ms) nếu gặp lỗi mạng tạm thời hoặc lỗi khác.
 * - Hỗ trợ hủy ngay lập tức qua cancel().
 */
export function createPoller(options: PollerOptions): PollerController {
  const {
    getStatus,
    onStatus,
    onError,
    now = () => Date.now(),
    initialDelayMs = 500,
    networkRetryDelayMs = 2500,
  } = options;

  let cancelled = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const startTime = now();

  async function tick() {
    try {
      const res = await getStatus();
      if (cancelled) return;
      onStatus(res);

      if (TERMINAL_STATUSES.has(res.status)) {
        return;
      }

      const elapsed = now() - startTime;
      const delay = nextPollDelay(elapsed);
      timer = setTimeout(tick, delay);
    } catch (err: unknown) {
      if (cancelled) return;
      const code =
        err instanceof ApiError
          ? err.code
          : err && typeof err === "object" && "code" in err && typeof (err as { code: unknown }).code === "string"
            ? (err as { code: string }).code
            : "NETWORK_ERROR";
      onError(code);
      if (code !== "SESSION_NOT_FOUND") {
        timer = setTimeout(tick, networkRetryDelayMs);
      }
    }
  }

  timer = setTimeout(tick, initialDelayMs);

  return {
    cancel() {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
    },
  };
}


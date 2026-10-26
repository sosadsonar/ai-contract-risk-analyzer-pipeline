import { useEffect, useRef, useState } from "react";
import { ApiError, getStatus } from "../api/client";
import type { SessionStatus, StatusResponse } from "../api/types";

const TERMINAL: Set<SessionStatus> = new Set(["COMPLETED", "FAILED", "REJECTED", "EXPIRED"]);

export function usePolling(sessionId: string) {
    const [status, setStatus] = useState<StatusResponse | null>(null);
    const [pollError, setPollError] = useState<string | null>(null);
    const [epoch, setEpoch] = useState(0); // tăng khi bấm Retry để khởi động lại chu kỳ poll
    const startTimeRef = useRef<number>(Date.now());

    useEffect(() => {
        let cancelled = false;
        let timer: ReturnType<typeof setTimeout> | null = null;
        startTimeRef.current = Date.now();

        async function tick() {
            try {
                const res = await getStatus(sessionId);
                if (cancelled) return;
                setStatus(res);
                setPollError(null);

                if (TERMINAL.has(res.status)) return;

                const elapsed = Date.now() - startTimeRef.current;
                const nextDelay = elapsed >= 60_000 ? 2500 : 1500;
                timer = setTimeout(tick, nextDelay);
            } catch (err) {
                if (cancelled) return;
                const code = err instanceof ApiError ? err.code : "NETWORK_ERROR";
                setPollError(code);
                // Nếu session không tồn tại thì dừng hẳn, lỗi mạng tạm thời thì thử lại sau 2.5s
                if (code !== "SESSION_NOT_FOUND") {
                    timer = setTimeout(tick, 2500);
                }
            }
        }

        // TDD §5.9 & NFR-PERF-02: poll lần đầu sau 500ms để hiển thị VALIDATING/PROCESSING <= 2s
        timer = setTimeout(tick, 500);

        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [sessionId, epoch]);

    function restartPolling(initialStatus?: StatusResponse) {
        if (initialStatus) setStatus(initialStatus);
        setPollError(null);
        setEpoch((n) => n + 1);
    }

    return { status, pollError, restartPolling };
}
import { useEffect, useState } from "react";
import { getStatus } from "../api/client";
import type { StatusResponse } from "../api/types";
import { createPoller } from "../lib/poller";

export function usePolling(sessionId: string) {
    const [status, setStatus] = useState<StatusResponse | null>(null);
    const [pollError, setPollError] = useState<string | null>(null);
    const [epoch, setEpoch] = useState(0); // tăng khi bấm Retry để khởi động lại chu kỳ poll

    useEffect(() => {
        const poller = createPoller({
            getStatus: () => getStatus(sessionId),
            onStatus: (res) => {
                setStatus(res);
                setPollError(null);
            },
            onError: (code) => {
                setPollError(code);
            },
        });

        return () => {
            poller.cancel();
        };
    }, [sessionId, epoch]);

    function restartPolling(initialStatus?: StatusResponse) {
        if (initialStatus) setStatus(initialStatus);
        setPollError(null);
        setEpoch((n) => n + 1);
    }

    return { status, pollError, restartPolling };
}

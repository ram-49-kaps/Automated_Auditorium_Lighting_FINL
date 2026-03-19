
import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Polling-based progress hook (replaces WebSocket to avoid Mixed Content issues).
 * Polls /api/results/{jobId} every few seconds until results are ready.
 */
export function useWebSocket(jobId) {
    const [status, setStatus] = useState('disconnected');
    const [messages, setMessages] = useState([]);
    const [latestMessage, setLatestMessage] = useState(null);
    const intervalRef = useRef(null);
    const phaseRef = useRef(1);

    const connect = useCallback(() => {
        if (!jobId || intervalRef.current) return;

        setStatus('connected');
        console.log('✅ Polling Started for job:', jobId);

        // Simulate phase progression while waiting for results
        let elapsed = 0;
        const PHASE_TIMINGS = [
            { phase: 1, title: 'Script Parsing', at: 0 },
            { phase: 2, title: 'Emotion Analysis', at: 8 },
            { phase: 3, title: 'Knowledge Retrieval', at: 20 },
            { phase: 4, title: 'Lighting Design', at: 35 },
            { phase: 6, title: 'Finalizing Output', at: 55 },
        ];

        intervalRef.current = setInterval(async () => {
            elapsed += 3;

            // Check if results are ready
            try {
                const response = await fetch(`/api/results/${jobId}`);

                if (response.ok) {
                    // Pipeline complete — results are ready!
                    clearInterval(intervalRef.current);
                    intervalRef.current = null;

                    const doneMsg = {
                        phase: 'done',
                        progress: 100,
                        detail: 'Pipeline complete!',
                        redirect: `/results/${jobId}`,
                    };
                    setLatestMessage(doneMsg);
                    setMessages((prev) => [...prev, doneMsg]);
                    setStatus('disconnected');
                    return;
                }
            } catch (err) {
                // Results not ready yet, continue polling
            }

            // Estimate current phase based on elapsed time
            let currentPhaseInfo = PHASE_TIMINGS[0];
            for (const pt of PHASE_TIMINGS) {
                if (elapsed >= pt.at) currentPhaseInfo = pt;
            }

            // Only send a message if phase changed
            const progress = Math.min(95, Math.round((elapsed / 70) * 100));
            const msg = {
                phase: currentPhaseInfo.phase,
                progress: progress,
                detail: `Processing ${currentPhaseInfo.title}...`,
                status: phaseRef.current !== currentPhaseInfo.phase ? 'started' : 'running',
            };

            // Mark previous phase as complete when moving to a new one
            if (phaseRef.current !== currentPhaseInfo.phase && phaseRef.current < currentPhaseInfo.phase) {
                const completeMsg = {
                    phase: phaseRef.current,
                    status: 'complete',
                    detail: 'Done',
                    stats: phaseRef.current === 1 ? { scenes: '—', format: 'auto' } :
                           phaseRef.current === 2 ? { detected: true } :
                           phaseRef.current === 4 ? { cues_generated: '—' } : {},
                };
                setLatestMessage(completeMsg);
                setMessages((prev) => [...prev, completeMsg]);
                phaseRef.current = currentPhaseInfo.phase;
            }

            setLatestMessage(msg);
            setMessages((prev) => [...prev, msg]);

            // Safety timeout after 5 minutes
            if (elapsed > 300) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
                const errorMsg = { phase: 'error', detail: 'Pipeline timeout — check server logs.' };
                setLatestMessage(errorMsg);
                setMessages((prev) => [...prev, errorMsg]);
                setStatus('error');
            }

        }, 3000); // Poll every 3 seconds

    }, [jobId]);

    const disconnect = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    // Auto-connect on mount if jobId is present
    useEffect(() => {
        if (jobId) {
            connect();
        }
        return () => disconnect();
    }, [jobId, connect, disconnect]);

    return { status, messages, latestMessage, connect, disconnect };
}

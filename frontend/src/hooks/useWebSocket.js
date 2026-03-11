
import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = '/api';

export function useWebSocket(jobId) {
    const [status, setStatus] = useState('disconnected');
    const [messages, setMessages] = useState([]);
    const [latestMessage, setLatestMessage] = useState(null);
    const intervalRef = useRef(null);
    const sinceRef = useRef(0);

    const connect = useCallback(() => {
        if (!jobId || intervalRef.current) return;

        setStatus('connecting');

        const poll = async () => {
            try {
                const res = await fetch(`${API_BASE}/progress/${jobId}?since=${sinceRef.current}`);
                if (!res.ok) return;

                const data = await res.json();
                if (data.messages && data.messages.length > 0) {
                    setStatus('connected');
                    for (const msg of data.messages) {
                        setLatestMessage(msg);
                        setMessages(prev => [...prev, msg]);
                    }
                    sinceRef.current = data.total;
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        };

        // Initial poll immediately
        poll();
        // Then poll every 2 seconds
        intervalRef.current = setInterval(poll, 2000);
    }, [jobId]);

    const disconnect = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }
    }, []);

    useEffect(() => {
        if (jobId) {
            connect();
        }
        return () => disconnect();
    }, [jobId, connect, disconnect]);

    return { status, messages, latestMessage, connect, disconnect };
}

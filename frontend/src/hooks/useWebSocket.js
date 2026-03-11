
import { useState, useEffect, useRef, useCallback } from 'react';

const WS_BASE_URL = 'ws://localhost:8000/ws/progress';

export function useWebSocket(jobId) {
    const [status, setStatus] = useState('disconnected'); // 'connecting', 'connected', 'disconnected', 'error'
    const [messages, setMessages] = useState([]);
    const [latestMessage, setLatestMessage] = useState(null);
    const wsRef = useRef(null);

    const connect = useCallback(() => {
        if (!jobId || wsRef.current) return;

        setStatus('connecting');
        const ws = new WebSocket(`${WS_BASE_URL}/${jobId}`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('✅ WebSocket Connected');
            setStatus('connected');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                setLatestMessage(data);
                setMessages((prev) => [...prev, data]);
            } catch (err) {
                console.error('Failed to parse WS message:', err);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket Error:', error);
            setStatus('error');
        };

        ws.onclose = () => {
            console.log('WebSocket Disconnected');
            setStatus('disconnected');
            wsRef.current = null;
        };

        return ws;
    }, [jobId]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
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

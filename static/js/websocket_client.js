/**
 * WebSocket client for real-time updates
 */

class WebSocketClient {
    constructor(url) {
        this.url = url;
        this.ws = null;
        this.reconnectInterval = 3000;
        this.listeners = [];
        this.connect();
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.notifyListeners(data);
                } catch (err) {
                    console.error('Failed to parse message:', err);
                }
            };

            this.ws.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.updateConnectionStatus(false);
                setTimeout(() => this.connect(), this.reconnectInterval);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (err) {
            console.error('Failed to connect:', err);
            setTimeout(() => this.connect(), this.reconnectInterval);
        }
    }

    on(callback) {
        this.listeners.push(callback);
    }

    notifyListeners(data) {
        this.listeners.forEach(callback => {
            try {
                callback(data);
            } catch (err) {
                console.error('Listener error:', err);
            }
        });
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    updateConnectionStatus(connected) {
        const statusEl = document.getElementById('connectionStatus');
        if (statusEl) {
            if (connected) {
                statusEl.textContent = '🟢 Connected';
                statusEl.className = 'status-connected';
            } else {
                statusEl.textContent = '🔴 Disconnected';
                statusEl.className = 'status-disconnected';
            }
        }
    }
}

// Create global WebSocket client
const wsClient = new WebSocketClient(`ws://${window.location.host}/ws`);
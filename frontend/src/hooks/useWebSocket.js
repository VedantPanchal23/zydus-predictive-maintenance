import { useEffect, useRef, useState } from 'react';

export function useWebSocket() {
  const [sensorData, setSensorData] = useState([]);
  const [latestAlert, setLatestAlert] = useState(null);
  const [connected, setConnected] = useState(false);
  const [summary, setSummary] = useState([]);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

    const connect = () => {
      socketRef.current = new WebSocket(`${wsUrl}/ws/live`);

      socketRef.current.onopen = () => setConnected(true);
      socketRef.current.onclose = () => {
        setConnected(false);
        reconnectTimerRef.current = window.setTimeout(connect, 3000);
      };

      socketRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'initial_summary') {
            setSummary(message.data);
          }

          if (message.type === 'sensor_update') {
            setSensorData(message.data);
          }

          if (message.type === 'critical_alert' || message.type === 'warning_alert') {
            setLatestAlert(message.data);
          }
        } catch {
          // Ignore malformed WebSocket payloads from reconnect or startup noise.
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current);
      }

      if (socketRef.current) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
    };
  }, []);

  return { sensorData, latestAlert, connected, summary, setLatestAlert };
}

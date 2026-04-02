import { useEffect, useRef, useState } from 'react'

export function useWebSocket() {
  const [sensorData, setSensorData] = useState([])
  const [latestAlert, setLatestAlert] = useState(null)
  const [connected, setConnected] = useState(false)
  const [summary, setSummary] = useState([])
  const ws = useRef(null)

  useEffect(() => {
    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    
    const connect = () => {
      ws.current = new WebSocket(`${WS_URL}/ws/live`)

      ws.current.onopen = () => setConnected(true)
      ws.current.onclose = () => {
        setConnected(false)
        // Reconnect after 3 seconds
        setTimeout(connect, 3000)
      }

      ws.current.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'initial_summary') setSummary(msg.data)
          if (msg.type === 'sensor_update') setSensorData(msg.data)
          if (msg.type === 'critical_alert' || msg.type === 'warning_alert') {
             setLatestAlert(msg.data)
          }
        } catch(e) { /* ignore parse errors */ }
      }
    }
    
    connect()

    return () => {
      if (ws.current) {
        ws.current.onclose = null // prevent reconnect loop on unmount
        ws.current.close()
      }
    }
  }, [])

  return { sensorData, latestAlert, connected, summary, setLatestAlert }
}

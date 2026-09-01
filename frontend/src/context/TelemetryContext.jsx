import React, { createContext, useContext, useState, useEffect } from "react";
import { wsClient } from "../services/websocket";

const TelemetryContext = createContext(null);

export function TelemetryProvider({ children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [liveReadings, setLiveReadings] = useState({});
  const [latestSummary, setLatestSummary] = useState(null);
  const [liveAlerts, setLiveAlerts] = useState([]);
  const [toastAlert, setToastAlert] = useState(null);

  useEffect(() => {
    wsClient.connect();

    const unsubStatus = wsClient.onStatusChange((status) => {
      setIsConnected(status);
    });

    const unsubMessage = wsClient.subscribe((msg) => {
      if (msg.type === "initial_summary") {
        setLatestSummary(msg.summary);
      } else if (msg.type === "sensor_update") {
        setLiveReadings((prev) => ({
          ...prev,
          [`${msg.equipment_id}:${msg.sensor_name}`]: msg,
        }));
      } else if (msg.type === "alert_triggered" || msg.type === "alert") {
        setLiveAlerts((prev) => [msg, ...prev.slice(0, 49)]);
        setToastAlert(msg);
        setTimeout(() => {
          setToastAlert(null);
        }, 6000);
      }
    });

    return () => {
      unsubStatus();
      unsubMessage();
    };
  }, []);

  return (
    <TelemetryContext.Provider
      value={{
        isConnected,
        liveReadings,
        latestSummary,
        liveAlerts,
        toastAlert,
        clearToast: () => setToastAlert(null),
      }}
    >
      {children}
    </TelemetryContext.Provider>
  );
}

export function useTelemetry() {
  const ctx = useContext(TelemetryContext);
  if (!ctx) throw new Error("useTelemetry must be used within a TelemetryProvider");
  return ctx;
}

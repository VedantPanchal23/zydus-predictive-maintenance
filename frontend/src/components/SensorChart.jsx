import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function SensorChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-md border border-slate-200 bg-slate-50">
        <p className="text-sm text-slate-500">No sensor data available.</p>
      </div>
    );
  }

  // Format the ISO UTC time efficiently
  const formattedData = data.map((item) => {
    const rawDate = new Date(item.timestamp);
    const label = rawDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return { ...item, label };
  });

  return (
    <div className="mt-4 h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickMargin={10}
            minTickGap={30}
          />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{ borderRadius: '6px', border: '1px solid #e2e8f0', boxShadow: 'none' }}
            itemStyle={{ color: '#0f172a', fontWeight: 500 }}
            labelStyle={{ color: '#475569', fontWeight: 500, marginBottom: '4px' }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#0f172a"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 5, fill: '#0f172a', strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

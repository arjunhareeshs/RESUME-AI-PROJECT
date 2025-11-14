import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from 'recharts';

// This data would come from an admin API endpoint
const scoreDistributionData = [
  { name: '0-20', count: 5 },
  { name: '21-40', count: 12 },
  { name: '41-60', count: 30 },
  { name: '61-80', count: 45 },
  { name: '81-100', count: 22 },
];

export const AnalyticsCharts: React.FC = () => {
  return (
    <div className="w-full h-80 bg-white p-4 rounded-lg shadow">
      <h3 className="font-semibold mb-4">ATS Score Distribution</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={scoreDistributionData}>
          <XAxis dataKey="name" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Bar dataKey="count" fill="#3B82F6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
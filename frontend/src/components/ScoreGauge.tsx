import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Label } from 'recharts';

interface Props {
  score: number;
  title: string;
}

export const ScoreGauge: React.FC<Props> = ({ score, title }) => {
  const data = [
    { name: 'Score', value: score },
    { name: 'Remaining', value: 100 - score },
  ];
  
  const color = score > 80 ? '#10B981' : score > 60 ? '#F59E0B' : '#EF4444';
  const COLORS = [color, '#E5E7EB'];

  return (
    <div className="w-40 h-36 flex flex-col items-center">
      <ResponsiveContainer width="100%" height={120}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={55}
            startAngle={180}
            endAngle={-180}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
            <Label 
              value={`${score}%`} 
              position="center" 
              className="text-2xl font-bold"
              fill="#111827"
            />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <p className="text-sm font-medium text-gray-600 -mt-4">{title}</p>
    </div>
  );
};
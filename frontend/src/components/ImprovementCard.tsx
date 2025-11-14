import React from 'react';

interface Props {
  improvement: {
    section: string;
    suggestion: string;
  };
}

export const ImprovementCard: React.FC<Props> = ({ improvement }) => {
  return (
    <div className="p-4 border border-yellow-300 bg-yellow-50 rounded-lg">
      <h4 className="font-semibold text-yellow-800">{improvement.section}</h4>
      <p className="text-sm text-yellow-700">{improvement.suggestion}</p>
    </div>
  );
};
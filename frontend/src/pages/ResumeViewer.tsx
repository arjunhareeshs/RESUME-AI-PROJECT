import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
// import { useGetResumeDetailsQuery } from '...';
import { useAnalyzeResumeMutation } from '../features/resume/resumeAPI';
import { AnalysisResult } from '../types';
import { ResumePreview } from '../components/ResumePreview';
import { ScoreGauge } from '../components/ScoreGauge';
import { ImprovementCard } from '../components/ImprovementCard';

export const ResumeViewer: React.FC = () => {
  const { resumeId } = useParams<{ resumeId: string }>();
  // const { data: resume, isLoading } = useGetResumeDetailsQuery(resumeId);
  const [analyzeResume, { data: analysis, isLoading: isAnalyzing }] = useAnalyzeResumeMutation();
  const [jd, setJd] = useState('');

  const handleAnalyze = () => {
    if (resumeId && jd) {
      analyzeResume({ resumeId: parseInt(resumeId), jd });
    }
  };
  
  // MOCK DATA until query is built
  const resume = { fileUrl: '/path/to/mock.pdf', ats_score: 85, role_match: 70 };
  const improvements = [{ id: 1, section: "Summary", suggestion: "Add metrics." }];

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Main Resume View */}
      <div className="flex-1 overflow-y-auto">
        {resume && <ResumePreview fileUrl={resume.fileUrl} />}
      </div>
      
      {/* Sidebar */}
      <aside className="w-1/3 h-full bg-white shadow-lg overflow-y-auto p-6">
        <h2 className="text-2xl font-bold mb-4">Resume Analysis</h2>
        
        {/* Scores */}
        <div className="flex justify-around mb-6">
          <ScoreGauge title="ATS Score" score={analysis && typeof analysis === 'object' && 'ats_compliance_score' in analysis ? (analysis as AnalysisResult).ats_compliance_score : resume.ats_score} />
          <ScoreGauge title="Role Match" score={analysis && typeof analysis === 'object' && 'role_match_percentage' in analysis ? (analysis as AnalysisResult).role_match_percentage : resume.role_match} />
        </div>

        {/* Analyze vs JD */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700">Job Description</label>
          <textarea 
            rows={6}
            className="w-full p-2 border rounded-md"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste job description here..."
          />
          <button 
            onClick={handleAnalyze} 
            disabled={isAnalyzing}
            className="w-full mt-2 px-4 py-2 bg-green-600 text-white rounded-lg"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
        
        {/* Improvements */}
        <div>
          <h3 className="text-xl font-semibold mb-3">AI Suggestions</h3>
          <div className="space-y-3">
            {improvements.map(imp => (
              <ImprovementCard key={imp.id} improvement={imp} />
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
};
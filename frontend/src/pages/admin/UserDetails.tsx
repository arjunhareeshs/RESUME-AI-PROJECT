import React from 'react';
import { useParams } from 'react-router-dom';
import { useGetUserDetailsQuery } from '../../features/admin/adminAPI';

interface UserDetailsResponse {
  user_info: {
    id: number;
    email: string;
    name: string;
    github_link?: string;
    leetcode_link?: string;
    github_stats?: Record<string, any>;
    leetcode_stats?: Record<string, any>;
  };
  resumes: Array<{
    id: number;
    file_type: string;
    created_at: string;
    ats_score: number;
    role_match: number;
  }>;
}

export const UserDetails: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const { data, isLoading } = useGetUserDetailsQuery(parseInt(userId!));

  if (isLoading) return <div>Loading user details...</div>;
  if (!data) return <div>User not found.</div>;

  const { user_info, resumes } = data as UserDetailsResponse;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-2">{user_info.name}</h1>
      <p className="text-lg text-gray-600 mb-6">{user_info.email}</p>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-6 mb-8">
        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="font-semibold mb-2">GitHub Stats</h3>
          <pre className="text-sm bg-gray-100 p-2 rounded">
            {JSON.stringify(user_info.github_stats, null, 2) ?? 'N/A'}
          </pre>
        </div>
        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="font-semibold mb-2">LeetCode Stats</h3>
          <pre className="text-sm bg-gray-100 p-2 rounded">
            {JSON.stringify(user_info.leetcode_stats, null, 2) ?? 'N/A'}
          </pre>
        </div>
      </div>

      {/* Resumes */}
      <h2 className="text-2xl font-semibold mb-4">User Resumes</h2>
      <div className="bg-white shadow rounded-lg divide-y divide-gray-200">
        {resumes.map((resume: any) => (
          <div key={resume.id} className="p-4 flex justify-between items-center">
            <div>
              <p className="font-medium">Resume ID: {resume.id} ({resume.file_type})</p>
              <p className="text-sm text-gray-500">Created: {new Date(resume.created_at).toLocaleString()}</p>
            </div>
            <div className="flex space-x-4">
              <span className="text-sm">ATS: <span className="font-bold">{resume.ats_score}%</span></span>
              <span className="text-sm">Match: <span className="font-bold">{resume.role_match}%</span></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
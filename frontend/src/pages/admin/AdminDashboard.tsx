import React from 'react';
import { AnalyticsCharts } from '../../components/AnalyticsCharts';
// import { useGetTopResumesQuery, useGetUsersQuery } from '../../features/admin/adminAPI';

export const AdminDashboard: React.FC = () => {
  // const { data: users } = useGetUsersQuery();
  // const { data: topResumes } = useGetTopResumesQuery(10);
  
  // MOCK DATA
  const users = { length: 50 };
  const newUsers = 5;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">Admin Dashboard</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-gray-500">Total Users</h3>
          <p className="text-4xl font-bold">{users?.length ?? 0}</p>
        </div>
        <div className="p-6 bg-white rounded-lg shadow">
          <h3 className="text-gray-500">New Users (24h)</h3>
          <p className="text-4xl font-bold">{newUsers}</p>
        </div>
      </div>
      
      {/* Charts */}
      <div>
        <h2 className="text-2xl font-semibold mb-4">Analytics</h2>
        <AnalyticsCharts />
      </div>
    </div>
  );
};
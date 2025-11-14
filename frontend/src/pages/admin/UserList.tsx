import React from 'react';
import { Link } from 'react-router-dom';
import { useGetUsersQuery } from '../../features/admin/adminAPI';

export const UserList: React.FC = () => {
  const { data: users, isLoading, error } = useGetUsersQuery(undefined);

  if (isLoading) return <div>Loading users...</div>;
  if (error) return <div>Error loading users.</div>;

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-6">User Management</h1>
      <div className="bg-white shadow rounded-lg">
        <table className="min-w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">GitHub</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {users && Array.isArray(users) ? users.map((user) => (
              <tr key={user.id}>
                <td className="px-6 py-4 whitespace-nowrap">{user.name}</td>
                <td className="px-6 py-4 whitespace-nowrap">{user.email}</td>
                <td className="px-6 py-4 whitespace-nowrap">{user.github_link ?? 'N/A'}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  <Link to={`/admin/user/${user.id}`} className="text-blue-600 hover:text-blue-900">
                    View
                  </Link>
                </td>
              </tr>
            )) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
};
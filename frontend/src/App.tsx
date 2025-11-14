import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { UploadPage } from './pages/UploadPage';
import { ResumeViewer } from './pages/ResumeViewer';
import { AdminDashboard } from './pages/admin/AdminDashboard';

function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/resume/:resumeId" element={<ResumeViewer />} />
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users/:userId" element={<AdminDashboard />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default App;

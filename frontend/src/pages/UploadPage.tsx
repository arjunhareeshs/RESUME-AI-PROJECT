import React, { useState } from 'react';
import { useUploadResumeMutation } from '../features/resume/resumeAPI';

export const UploadPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploadResume, { isLoading, data, error }] = useUploadResumeMutation();
  
  type UploadResponse = { resume_id: number };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    
    try {
      // This triggers the upload
      await uploadResume(file).unwrap();
      // On success, 'data' will have { resume_id: ... }
      // You can then navigate to the viewer page
      // navigate(`/resume/${data.resume_id}`);
    } catch (err) {
      console.error('Failed to upload:', err);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Upload or Generate Resume</h1>
      
      {/* TODO: Add tabs for Upload vs Generate */}
      
      <form onSubmit={handleSubmit} className="border p-6 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Upload a file</h2>
        <input 
          type="file" 
          onChange={handleFileChange} 
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          accept=".pdf,.docx,.jpg,.png"
        />
        <button 
          type="submit" 
          disabled={!file || isLoading}
          className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg disabled:bg-gray-400"
        >
          {isLoading ? 'Uploading...' : 'Upload'}
        </button>
        {data ? (
          <p className="text-green-600 mt-2">
            Success! Resume ID: {(data as UploadResponse).resume_id}
          </p>
        ) : null}
        {error ? (
          <p className="text-red-600 mt-2">
            Upload failed: {error && typeof error === 'object' && 'data' in error ? String(error.data) : 'Unknown error'}
          </p>
        ) : null}
      </form>
    </div>
  );
};
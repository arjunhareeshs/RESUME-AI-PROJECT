import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { Resume, AnalysisResult } from '../../types';

// Define endpoints based on your user API
export const resumeApi = createApi({
  reducerPath: 'resumeApi',
  baseQuery: fetchBaseQuery({ 
    baseUrl: '/api/v1/user',
    prepareHeaders: (headers) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      return headers;
    }
  }),
  tagTypes: ['Resumes'],
  endpoints: (builder: any) => ({
    // @ts-expect-error - RTK Query types not fully resolved
    getUserResumes: builder.query<Resume[], void>({
      query: () => '/get_user_resumes',
      providesTags: ['Resumes'],
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    uploadResume: builder.mutation<{ resume_id: number }, File>({
      query: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return {
          url: '/upload_resume',
          method: 'POST',
          body: formData,
        };
      },
      invalidatesTags: ['Resumes'],
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    extractResume: builder.mutation<Resume, number>({
      query: (resumeId: number) => ({
        url: `/extract_resume?resume_id=${resumeId}`,
        method: 'POST',
      }),
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    analyzeResume: builder.mutation<AnalysisResult, { resumeId: number; jd: string }>({
      query: ({ resumeId, jd }: { resumeId: number; jd: string }) => ({
        url: `/analyze_resume?resume_id=${resumeId}`,
        method: 'POST',
        body: { job_description: jd },
        headers: {
          'Content-Type': 'application/json',
        },
      }),
    }),
  }),
});

export const { 
  useGetUserResumesQuery,
  useUploadResumeMutation,
  useExtractResumeMutation,
  useAnalyzeResumeMutation,
} = resumeApi;
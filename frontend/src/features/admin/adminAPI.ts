import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { User } from '../../types';

export const adminApi = createApi({
  reducerPath: 'adminApi',
  baseQuery: fetchBaseQuery({ 
    baseUrl: '/api/v1/admin',
    // prepareHeaders: (headers, { getState }) => ... set auth token
  }),
  tagTypes: ['Users', 'TopResumes'],
  endpoints: (builder: any) => ({
    // @ts-expect-error - RTK Query types not fully resolved
    getUsers: builder.query<User[], void>({
      query: () => '/users',
      providesTags: ['Users'],
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    getUserDetails: builder.query<any, number>({
      query: (userId: number) => `/user/${userId}`,
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    getTopResumes: builder.query<any[], number>({
      query: (n: number) => `/top_resumes?n=${n}`,
      providesTags: ['TopResumes'],
    }),
  }),
});

export const { 
  useGetUsersQuery,
  useGetUserDetailsQuery,
  useGetTopResumesQuery,
} = adminApi;
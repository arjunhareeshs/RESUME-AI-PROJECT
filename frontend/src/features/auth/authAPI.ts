import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { User } from '../../types';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = createApi({
  reducerPath: 'authApi',
  baseQuery: fetchBaseQuery({ 
    baseUrl: '/api/v1/auth',
    // prepareHeaders: (headers, { getState }) => ... set auth token
  }),
  tagTypes: ['Auth'],
  endpoints: (builder: any) => ({
    // @ts-expect-error - RTK Query types not fully resolved
    login: builder.mutation<AuthResponse, LoginRequest>({
      query: (credentials: LoginRequest) => ({
        url: '/token',
        method: 'POST',
        body: new URLSearchParams({
          username: credentials.email,
          password: credentials.password,
        }),
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      }),
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    register: builder.mutation<AuthResponse, RegisterRequest>({
      query: (userData: RegisterRequest) => ({
        url: '/register',
        method: 'POST',
        body: userData,
      }),
    }),
    // @ts-expect-error - RTK Query types not fully resolved
    getCurrentUser: builder.query<User, void>({
      query: () => '/me',
      providesTags: ['Auth'],
    }),
  }),
});

export const { 
  useLoginMutation,
  useRegisterMutation,
  useGetCurrentUserQuery,
} = authApi;


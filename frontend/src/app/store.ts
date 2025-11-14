import { configureStore } from '@reduxjs/toolkit';
import rootReducer from './rootReducer';
import { resumeApi } from '../features/resume/resumeAPI';
import { adminApi } from '../features/admin/adminAPI';
import { authApi } from '../features/auth/authAPI';

export const store = configureStore({
  reducer: rootReducer,
  middleware: (getDefaultMiddleware: any) =>
    getDefaultMiddleware().concat(
      authApi.middleware,
      resumeApi.middleware,
      adminApi.middleware
    ),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
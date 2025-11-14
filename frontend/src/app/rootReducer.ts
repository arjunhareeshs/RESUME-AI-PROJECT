import { combineReducers } from '@reduxjs/toolkit';
import authReducer from '../features/auth/authSlice';
import resumeReducer from '../features/resume/resumeSlice';
import { authApi } from '../features/auth/authAPI';
import { resumeApi } from '../features/resume/resumeAPI';
import { adminApi } from '../features/admin/adminAPI';

const rootReducer = combineReducers({
  auth: authReducer,
  resume: resumeReducer,
  [authApi.reducerPath]: authApi.reducer,
  [resumeApi.reducerPath]: resumeApi.reducer,
  [adminApi.reducerPath]: adminApi.reducer,
});

export default rootReducer;
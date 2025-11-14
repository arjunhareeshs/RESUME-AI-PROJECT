import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AnalysisResult, Resume } from '../../types';
import { resumeApi } from './resumeAPI';
import { RootState } from '../../app/store';

// Define the shape of the local resume state
interface ResumeState {
  /** The ID of the resume currently being viewed */
  selectedResumeId: number | null;
  
  /** The full data of the currently selected resume (optional, can be hydrated) */
  selectedResume: Resume | null;
  
  /** The results of the last successful analysis */
  currentAnalysis: AnalysisResult | null;
  
  /** UI state for controlling the analysis sidebar */
  isAnalysisPanelOpen: boolean;
}

// Set the initial state
const initialState: ResumeState = {
  selectedResumeId: null,
  selectedResume: null,
  currentAnalysis: null,
  isAnalysisPanelOpen: true,
};

const resumeSlice = createSlice({
  name: 'resume',
  initialState,
  
  // Reducers for actions dispatched directly
  reducers: {
    /** Sets the active resume ID when a user clicks one */
    setSelectedResume: (state, action: PayloadAction<Resume | null>) => {
      state.selectedResume = action.payload;
      state.selectedResumeId = action.payload?.id ?? null;
      // Clear old analysis when viewing a new resume
      state.currentAnalysis = null;
    },
    
    /** Toggles the visibility of the analysis sidebar */
    toggleAnalysisPanel: (state) => {
      state.isAnalysisPanelOpen = !state.isAnalysisPanelOpen;
    },
    
    /** Clears the current analysis results */
    clearAnalysis: (state) => {
      state.currentAnalysis = null;
    },
  },
  
  // Extra reducers to react to API call completion from resumeAPI.ts
  extraReducers: (builder) => {
    // When the 'analyzeResume' mutation is successful, store its result
    builder.addMatcher(
      resumeApi.endpoints.analyzeResume.matchFulfilled,
      (state, action) => {
        state.currentAnalysis = action.payload as AnalysisResult;
      }
    );
    
    // When a resume is successfully uploaded, auto-select it
    builder.addMatcher(
      resumeApi.endpoints.uploadResume.matchFulfilled,
      (state, action) => {
        // We only have the ID, so we set this.
        // The UI should then trigger a refetch of /get_user_resumes
        // or a new query to get this specific resume's details.
        const payload = action.payload as { resume_id: number };
        state.selectedResumeId = payload.resume_id;
      }
    );
    
    // When the full list of resumes is fetched, if we have a selected ID
    // but no data, find the matching resume and populate it.
    builder.addMatcher(
      resumeApi.endpoints.getUserResumes.matchFulfilled,
      (state, action) => {
        const resumes = action.payload as Resume[];
        if (state.selectedResumeId && !state.selectedResume) {
          const found = resumes.find(r => r.id === state.selectedResumeId);
          if (found) {
            state.selectedResume = found;
          }
        }
      }
    );
  },
});

// Export the actions for use in components
export const { setSelectedResume, toggleAnalysisPanel, clearAnalysis } = resumeSlice.actions;

// Export selectors to easily get data from this slice
export const selectSelectedResume = (state: RootState) => state.resume.selectedResume;
export const selectCurrentAnalysis = (state: RootState) => state.resume.currentAnalysis;
export const selectIsAnalysisPanelOpen = (state: RootState) => state.resume.isAnalysisPanelOpen;

// Export the reducer to be added to the store
export default resumeSlice.reducer;
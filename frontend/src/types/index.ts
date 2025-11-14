export interface User {
    id: number;
    email: string;
    name: string;
    github_link?: string;
    leetcode_link?: string;
    github_stats?: Record<string, any>;
    leetcode_stats?: Record<string, any>;
  }
  
  export interface Resume {
    id: number;
    user_id: number;
    file_type: string;
    ats_score: number;
    role_match: number;
    created_at: string;
    extracted_data?: Record<string, any>;
  }
  
  export interface Improvement {
    id: number;
    resume_id: number;
    section: string;
    suggestion: string;
    old_text?: string;
  }
  
  export interface AnalysisResult {
    ats_compliance_score: number;
    role_match_percentage: number;
    keyword_coverage: {
      missing_keywords: string[];
    };
  }
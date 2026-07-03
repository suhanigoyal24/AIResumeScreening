// src/types/index.ts

export interface MatchReport {
  matched_keywords: string[];
  missing_keywords: string[];
  section_scores: {
    skills: number;
    experience: number;
    education: number;
    keywords: number;
  };
  recommendations: string[];
}


export interface UploadResumeProps {
  onUpload?: (candidate: Candidate) => void;
  onBatchComplete?: () => void;
}

export interface CandidateCardProps extends Candidate {}

export interface DashboardState {
  candidates: Candidate[];
  loading: boolean;
  search: string;
  minScore: number;
}

export interface Candidate {
  id?: number;
  name: string;
  score: number;
  skills?: string[];
  resume_url?: string;
  matched_keywords?: string[];
  [key: string]: any;
}
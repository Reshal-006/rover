export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export interface Finding {
  id: string;
  scan_id: string;
  repository_url?: string;
  title: string;
  description: string;
  severity: SeverityLevel;
  category: string;
  confidence: number;
  impact: string;
  filepath: string;
  line_number: number;
  code_snippet?: string;
  reasoning?: string;
  suggested_fix?: string;
  created_at: string;
  is_fixed?: boolean;
}

export interface ScanResult {
  scan_id: string;
  repository: string;
  status: 'scanning' | 'completed' | 'failed';
  phase: 'cloning' | 'traversal' | 'static_analysis' | 'llm_analysis' | 'ranking' | 'completed' | 'failed';
  progress: number;
  current_file?: string;
  files_scanned: number;
  ignored_files: number;
  scan_duration_seconds: number;
  language_breakdown?: Record<string, number>;
  bugs: Finding[];
  error?: string;
  timestamp: string;
}

export interface FixRun {
  fix_id: string;
  status: 'running' | 'completed' | 'failed';
  issue_number?: number;
  pull_request_number?: number;
  pull_request_url?: string;
  summary?: string;
  duration_seconds?: number;
}

export interface Repository {
  id: string;
  full_name: string;
  default_branch: string;
  is_private: boolean;
  last_scanned_at?: string;
}

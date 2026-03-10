export interface Execution {
  id: string;
  job_id: string;
  job_name: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  exit_code: number | null;
  status: 'running' | 'success' | 'failed' | 'timeout' | 'killed';
  stdout: string;
  stderr: string;
  triggered_by: string;
  retry_number: number;
  pid: number | null;
}

export interface ExecutionListResponse {
  items: Execution[];
  total: number;
  page: number;
  page_size: number;
}

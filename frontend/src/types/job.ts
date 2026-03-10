export interface Job {
  id: string;
  name: string;
  description: string;
  command: string;
  cron_expression: string;
  working_directory: string;
  environment_vars: Record<string, string>;
  shell_type: string;
  timeout_seconds: number;
  max_retries: number;
  retry_delay_seconds: number;
  allow_concurrent: boolean;
  is_enabled: boolean;
  is_running: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFormData {
  name: string;
  description: string;
  command: string;
  cron_expression: string;
  working_directory: string;
  environment_vars: Record<string, string>;
  shell_type: string;
  timeout_seconds: number;
  max_retries: number;
  retry_delay_seconds: number;
  allow_concurrent: boolean;
  is_enabled: boolean;
}

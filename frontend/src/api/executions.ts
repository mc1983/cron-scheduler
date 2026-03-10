import client from './client';
import type { Execution, ExecutionListResponse } from '../types/execution';

export const getExecutions = async (params?: {
  job_id?: string;
  status?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}): Promise<ExecutionListResponse> => {
  const { data } = await client.get('/executions', { params });
  return data;
};

export const getExecution = async (id: string): Promise<Execution> => {
  const { data } = await client.get(`/executions/${id}`);
  return data;
};

export const killExecution = async (id: string): Promise<void> => {
  await client.post(`/executions/${id}/kill`);
};

export const deleteExecution = async (id: string): Promise<void> => {
  await client.delete(`/executions/${id}`);
};

export const getStats = async (): Promise<{
  total_jobs: number;
  enabled_jobs: number;
  running_jobs: number;
  executions_24h: number;
  success_24h: number;
  failed_24h: number;
}> => {
  const { data } = await client.get('/stats');
  return data;
};

import client from './client';
import type { Job, JobListResponse, JobFormData } from '../types/job';

export const getJobs = async (params?: {
  page?: number;
  page_size?: number;
  is_enabled?: boolean;
  search?: string;
}): Promise<JobListResponse> => {
  const { data } = await client.get('/jobs', { params });
  return data;
};

export const getJob = async (id: string): Promise<Job> => {
  const { data } = await client.get(`/jobs/${id}`);
  return data;
};

export const createJob = async (payload: JobFormData): Promise<Job> => {
  const { data } = await client.post('/jobs', payload);
  return data;
};

export const updateJob = async (id: string, payload: Partial<JobFormData>): Promise<Job> => {
  const { data } = await client.put(`/jobs/${id}`, payload);
  return data;
};

export const deleteJob = async (id: string): Promise<void> => {
  await client.delete(`/jobs/${id}`);
};

export const runJobNow = async (id: string): Promise<void> => {
  await client.post(`/jobs/${id}/run`);
};

export const pauseJob = async (id: string): Promise<Job> => {
  const { data } = await client.post(`/jobs/${id}/pause`);
  return data;
};

export const resumeJob = async (id: string): Promise<Job> => {
  const { data } = await client.post(`/jobs/${id}/resume`);
  return data;
};

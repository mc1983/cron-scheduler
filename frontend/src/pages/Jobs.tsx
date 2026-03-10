import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getJobs, createJob, updateJob, deleteJob, runJobNow, pauseJob, resumeJob } from '../api/jobs';
import { getExecutions } from '../api/executions';
import { StatusBadge } from '../components/StatusBadge';
import { JobForm } from '../components/JobForm';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { ExecutionLog } from '../components/ExecutionLog';
import type { Job, JobFormData } from '../types/job';

export function Jobs() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editJob, setEditJob] = useState<Job | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Job | null>(null);
  const [selectedExec, setSelectedExec] = useState<string | null>(null);
  const [expandedJob, setExpandedJob] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['jobs', { page, search }],
    queryFn: () => getJobs({ page, page_size: 20, search: search || undefined }),
    refetchInterval: 15000,
  });

  const { data: jobExecs } = useQuery({
    queryKey: ['executions', { job_id: expandedJob }],
    queryFn: () => getExecutions({ job_id: expandedJob!, page_size: 5 }),
    enabled: !!expandedJob,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['jobs'] });

  const createMut = useMutation({ mutationFn: createJob, onSuccess: invalidate });
  const updateMut = useMutation({ mutationFn: ({ id, data }: { id: string; data: Partial<JobFormData> }) => updateJob(id, data), onSuccess: invalidate });
  const deleteMut = useMutation({ mutationFn: deleteJob, onSuccess: invalidate });
  const runMut = useMutation({ mutationFn: runJobNow, onSuccess: invalidate });
  const pauseMut = useMutation({ mutationFn: pauseJob, onSuccess: invalidate });
  const resumeMut = useMutation({ mutationFn: resumeJob, onSuccess: invalidate });

  const handleSubmit = async (formData: JobFormData) => {
    if (editJob) {
      await updateMut.mutateAsync({ id: editJob.id, data: formData });
      setEditJob(null);
    } else {
      await createMut.mutateAsync(formData);
      setShowForm(false);
    }
  };

  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Jobs</h1>
        <button className="btn-primary" onClick={() => setShowForm(true)}>+ New Job</button>
      </div>

      <div className="toolbar">
        <input
          className="search-input"
          placeholder="Search jobs..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <span className="toolbar-count">{data?.total ?? 0} jobs</span>
      </div>

      {isLoading ? (
        <p className="loading-text">Loading...</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Schedule</th>
                <th>Status</th>
                <th>Last Run</th>
                <th>Next Run</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map(job => (
                <>
                  <tr key={job.id} className={`job-row ${!job.is_enabled ? 'job-disabled' : ''}`}>
                    <td>
                      <button className="btn-link job-name" onClick={() => setExpandedJob(expandedJob === job.id ? null : job.id)}>
                        {job.name}
                      </button>
                      {job.description && <div className="job-desc">{job.description}</div>}
                    </td>
                    <td className="font-mono text-sm">{job.cron_expression}</td>
                    <td>
                      <StatusBadge status={job.last_status} isRunning={job.is_running} />
                      {!job.is_enabled && <span className="badge badge-neutral ml-1">Paused</span>}
                    </td>
                    <td className="text-sm text-muted">
                      {job.last_run_at ? new Date(job.last_run_at).toLocaleString() : '—'}
                    </td>
                    <td className="text-sm text-muted">
                      {job.next_run_at ? new Date(job.next_run_at).toLocaleString() : '—'}
                    </td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="btn-action btn-run"
                          title="Run Now"
                          disabled={!job.is_enabled || runMut.isPending}
                          onClick={() => runMut.mutate(job.id)}
                        >▶</button>
                        <button
                          className="btn-action"
                          title={job.is_enabled ? 'Pause' : 'Resume'}
                          onClick={() => job.is_enabled ? pauseMut.mutate(job.id) : resumeMut.mutate(job.id)}
                        >{job.is_enabled ? '⏸' : '▶▶'}</button>
                        <button
                          className="btn-action"
                          title="Edit"
                          onClick={() => setEditJob(job)}
                        >✏</button>
                        <button
                          className="btn-action btn-delete"
                          title="Delete"
                          onClick={() => setDeleteTarget(job)}
                        >🗑</button>
                      </div>
                    </td>
                  </tr>
                  {expandedJob === job.id && (
                    <tr key={`${job.id}-expanded`} className="expanded-row">
                      <td colSpan={6}>
                        <div className="expanded-content">
                          <div className="expanded-meta">
                            <strong>Command:</strong> <code>{job.command}</code>
                            {job.working_directory && <><strong>CWD:</strong> <code>{job.working_directory}</code></>}
                            <strong>Shell:</strong> {job.shell_type}
                            <strong>Timeout:</strong> {job.timeout_seconds}s
                            <strong>Retries:</strong> {job.max_retries}
                          </div>
                          <div className="expanded-execs">
                            <strong>Recent executions:</strong>
                            {jobExecs?.items.map(exec => (
                              <div key={exec.id} className="mini-exec-row">
                                <StatusBadge status={exec.status} isRunning={exec.status === 'running'} />
                                <span>{new Date(exec.started_at).toLocaleString()}</span>
                                <span>{exec.duration_ms !== null ? `${(exec.duration_ms/1000).toFixed(1)}s` : '...'}</span>
                                <button className="btn-link" onClick={() => setSelectedExec(exec.id)}>Logs</button>
                              </div>
                            ))}
                            {!jobExecs?.items.length && <span className="text-muted">No executions yet</span>}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
              {!data?.items.length && (
                <tr><td colSpan={6} className="table-empty">No jobs found. Create your first job!</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="pagination">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-secondary btn-sm">Prev</button>
          <span>Page {page} of {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="btn-secondary btn-sm">Next</button>
        </div>
      )}

      {(showForm || editJob) && (
        <JobForm
          initial={editJob}
          onSubmit={handleSubmit}
          onCancel={() => { setShowForm(false); setEditJob(null); }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          message={`Delete job "${deleteTarget.name}" and all its execution history?`}
          onConfirm={() => { deleteMut.mutate(deleteTarget.id); setDeleteTarget(null); }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}

      {selectedExec && (
        <ExecutionLog execId={selectedExec} onClose={() => setSelectedExec(null)} />
      )}
    </div>
  );
}

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getExecutions } from '../api/executions';
import { StatusBadge } from '../components/StatusBadge';
import { ExecutionLog } from '../components/ExecutionLog';

const STATUS_OPTIONS = ['', 'running', 'success', 'failed', 'timeout', 'killed'];

export function Executions() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState('');
  const [selectedExec, setSelectedExec] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['executions', { page, status }],
    queryFn: () => getExecutions({ page, page_size: 30, status: status || undefined }),
    refetchInterval: 10000,
  });

  const totalPages = data ? Math.ceil(data.total / 30) : 1;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Execution History</h1>
      </div>

      <div className="toolbar">
        <select className="filter-select" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s || 'All statuses'}</option>)}
        </select>
        <span className="toolbar-count">{data?.total ?? 0} executions</span>
      </div>

      {isLoading ? (
        <p className="loading-text">Loading...</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Job</th>
                <th>Status</th>
                <th>Trigger</th>
                <th>Exit Code</th>
                <th>Started</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map(exec => (
                <tr key={exec.id}>
                  <td>{exec.job_name ?? exec.job_id}</td>
                  <td><StatusBadge status={exec.status} isRunning={exec.status === 'running'} /></td>
                  <td>{exec.triggered_by}{exec.retry_number > 0 ? ` (retry #${exec.retry_number})` : ''}</td>
                  <td className="font-mono">{exec.exit_code ?? '—'}</td>
                  <td className="text-sm">{new Date(exec.started_at).toLocaleString()}</td>
                  <td className="text-sm">
                    {exec.duration_ms !== null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '...'}
                  </td>
                  <td>
                    <button className="btn-link" onClick={() => setSelectedExec(exec.id)}>Logs</button>
                  </td>
                </tr>
              ))}
              {!data?.items.length && (
                <tr><td colSpan={7} className="table-empty">No executions found</td></tr>
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

      {selectedExec && (
        <ExecutionLog execId={selectedExec} onClose={() => setSelectedExec(null)} />
      )}
    </div>
  );
}

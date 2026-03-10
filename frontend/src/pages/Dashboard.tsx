import { useQuery } from '@tanstack/react-query';
import { getStats } from '../api/executions';
import { getExecutions } from '../api/executions';
import { StatusBadge } from '../components/StatusBadge';
import { useState } from 'react';
import { ExecutionLog } from '../components/ExecutionLog';

export function Dashboard() {
  const [selectedExec, setSelectedExec] = useState<string | null>(null);

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: getStats,
    refetchInterval: 10000,
  });

  const { data: recent } = useQuery({
    queryKey: ['executions', { page_size: 10 }],
    queryFn: () => getExecutions({ page_size: 10 }),
    refetchInterval: 10000,
  });

  const successRate = stats && stats.executions_24h > 0
    ? Math.round((stats.success_24h / stats.executions_24h) * 100)
    : null;

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats?.total_jobs ?? '—'}</div>
          <div className="stat-label">Total Jobs</div>
        </div>
        <div className="stat-card stat-card-green">
          <div className="stat-value">{stats?.enabled_jobs ?? '—'}</div>
          <div className="stat-label">Enabled</div>
        </div>
        <div className="stat-card stat-card-blue">
          <div className="stat-value">{stats?.running_jobs ?? '—'}</div>
          <div className="stat-label">Running Now</div>
        </div>
        <div className="stat-card stat-card-green">
          <div className="stat-value">{stats?.success_24h ?? '—'}</div>
          <div className="stat-label">Success (24h)</div>
        </div>
        <div className="stat-card stat-card-red">
          <div className="stat-value">{stats?.failed_24h ?? '—'}</div>
          <div className="stat-label">Failed (24h)</div>
        </div>
        {successRate !== null && (
          <div className="stat-card">
            <div className="stat-value">{successRate}%</div>
            <div className="stat-label">Success Rate (24h)</div>
          </div>
        )}
      </div>

      <h2 className="section-title">Recent Executions</h2>
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Status</th>
              <th>Trigger</th>
              <th>Started</th>
              <th>Duration</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {recent?.items.map(exec => (
              <tr key={exec.id}>
                <td>{exec.job_name}</td>
                <td><StatusBadge status={exec.status} isRunning={exec.status === 'running'} /></td>
                <td>{exec.triggered_by}</td>
                <td>{new Date(exec.started_at).toLocaleString()}</td>
                <td>{exec.duration_ms !== null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '—'}</td>
                <td>
                  <button className="btn-link" onClick={() => setSelectedExec(exec.id)}>Logs</button>
                </td>
              </tr>
            ))}
            {!recent?.items.length && (
              <tr><td colSpan={6} className="table-empty">No executions yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedExec && (
        <ExecutionLog execId={selectedExec} onClose={() => setSelectedExec(null)} />
      )}
    </div>
  );
}

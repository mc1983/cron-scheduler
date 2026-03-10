import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getExecution, killExecution } from '../api/executions';
import { StatusBadge } from './StatusBadge';

interface Props {
  execId: string;
  onClose: () => void;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return '—';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  return `${m}m ${s}s`;
}

export function ExecutionLog({ execId, onClose }: Props) {
  const [tab, setTab] = useState<'stdout' | 'stderr'>('stdout');
  const { data: exec, isLoading } = useQuery({
    queryKey: ['execution', execId],
    queryFn: () => getExecution(execId),
    refetchInterval: (q) => q.state.data?.status === 'running' ? 2000 : false,
  });

  const handleKill = async () => {
    await killExecution(execId);
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box modal-box-lg" onClick={e => e.stopPropagation()}>
        <div className="log-header">
          <h2 className="modal-title">Execution Log</h2>
          <button className="btn-icon" onClick={onClose}>✕</button>
        </div>

        {isLoading ? (
          <p className="loading-text">Loading...</p>
        ) : exec ? (
          <>
            <div className="log-meta">
              <StatusBadge status={exec.status} isRunning={exec.status === 'running'} />
              <span>PID: {exec.pid ?? '—'}</span>
              <span>Exit: {exec.exit_code ?? '—'}</span>
              <span>Duration: {formatDuration(exec.duration_ms)}</span>
              <span>Trigger: {exec.triggered_by}</span>
              {exec.retry_number > 0 && <span>Retry #{exec.retry_number}</span>}
              {exec.status === 'running' && (
                <button className="btn-danger btn-sm" onClick={handleKill}>Kill</button>
              )}
            </div>
            <div className="log-meta-time">
              <span>Started: {new Date(exec.started_at).toLocaleString()}</span>
              {exec.finished_at && <span>Finished: {new Date(exec.finished_at).toLocaleString()}</span>}
            </div>

            <div className="log-tabs">
              <button className={`log-tab ${tab === 'stdout' ? 'active' : ''}`} onClick={() => setTab('stdout')}>
                stdout
              </button>
              <button className={`log-tab ${tab === 'stderr' ? 'active' : ''}`} onClick={() => setTab('stderr')}>
                stderr {exec.stderr ? '(!)' : ''}
              </button>
            </div>
            <pre className="log-output">
              {(tab === 'stdout' ? exec.stdout : exec.stderr) || <span className="log-empty">(empty)</span>}
            </pre>
          </>
        ) : <p>Not found</p>}
      </div>
    </div>
  );
}

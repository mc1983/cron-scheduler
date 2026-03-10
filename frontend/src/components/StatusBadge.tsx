interface Props {
  status: string | null;
  isRunning?: boolean;
}

const statusConfig: Record<string, { label: string; className: string }> = {
  success: { label: 'Success', className: 'badge-success' },
  failed:  { label: 'Failed',  className: 'badge-error' },
  timeout: { label: 'Timeout', className: 'badge-warning' },
  killed:  { label: 'Killed',  className: 'badge-warning' },
  running: { label: 'Running', className: 'badge-running' },
};

export function StatusBadge({ status, isRunning }: Props) {
  const key = isRunning ? 'running' : (status ?? 'unknown');
  const cfg = statusConfig[key] ?? { label: key, className: 'badge-neutral' };
  return <span className={`badge ${cfg.className}`}>{cfg.label}</span>;
}

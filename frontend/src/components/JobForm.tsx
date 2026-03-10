import { useState } from 'react';
import type { Job, JobFormData } from '../types/job';

interface Props {
  initial?: Job | null;
  onSubmit: (data: JobFormData) => Promise<void>;
  onCancel: () => void;
}

const SHELL_OPTIONS = ['auto', 'cmd', 'powershell', 'bash', 'sh'];

const DEFAULT_FORM: JobFormData = {
  name: '',
  description: '',
  command: '',
  cron_expression: '* * * * *',
  working_directory: '',
  environment_vars: {},
  shell_type: 'auto',
  timeout_seconds: 3600,
  max_retries: 0,
  retry_delay_seconds: 60,
  allow_concurrent: false,
  is_enabled: true,
};

function describeCron(expr: string): string {
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) return 'Invalid expression (need 5 fields)';
  const [min, hour, dom, mon, dow] = parts;
  if (expr === '* * * * *') return 'Every minute';
  if (min === '0' && hour === '*') return `Every hour at :00`;
  if (min !== '*' && hour !== '*' && dom === '*' && mon === '*' && dow === '*')
    return `Daily at ${hour.padStart(2,'0')}:${min.padStart(2,'0')}`;
  return `${min} ${hour} ${dom} ${mon} ${dow}`;
}

export function JobForm({ initial, onSubmit, onCancel }: Props) {
  const [form, setForm] = useState<JobFormData>(
    initial ? {
      name: initial.name,
      description: initial.description,
      command: initial.command,
      cron_expression: initial.cron_expression,
      working_directory: initial.working_directory,
      environment_vars: initial.environment_vars,
      shell_type: initial.shell_type,
      timeout_seconds: initial.timeout_seconds,
      max_retries: initial.max_retries,
      retry_delay_seconds: initial.retry_delay_seconds,
      allow_concurrent: initial.allow_concurrent,
      is_enabled: initial.is_enabled,
    } : DEFAULT_FORM
  );
  const [envRows, setEnvRows] = useState<Array<{ key: string; value: string }>>(
    Object.entries(form.environment_vars).map(([key, value]) => ({ key, value }))
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const set = (field: keyof JobFormData, value: unknown) =>
    setForm(f => ({ ...f, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const env: Record<string, string> = {};
    for (const row of envRows) {
      if (row.key.trim()) env[row.key.trim()] = row.value;
    }
    try {
      setLoading(true);
      await onSubmit({ ...form, environment_vars: env });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>
        <h2 className="modal-title">{initial ? 'Edit Job' : 'New Job'}</h2>
        <form onSubmit={handleSubmit} className="form">
          {error && <div className="form-error">{error}</div>}

          <div className="form-row">
            <label>Name *</label>
            <input required value={form.name} onChange={e => set('name', e.target.value)} placeholder="My Backup Job" />
          </div>

          <div className="form-row">
            <label>Description</label>
            <input value={form.description} onChange={e => set('description', e.target.value)} placeholder="Optional description" />
          </div>

          <div className="form-row">
            <label>Command *</label>
            <input required value={form.command} onChange={e => set('command', e.target.value)} placeholder="python script.py" className="font-mono" />
          </div>

          <div className="form-row">
            <label>
              Cron Expression *
              <span className="cron-hint">{describeCron(form.cron_expression)}</span>
            </label>
            <input
              required
              value={form.cron_expression}
              onChange={e => set('cron_expression', e.target.value)}
              placeholder="* * * * *"
              className="font-mono"
            />
            <small className="field-hint">min hour dom month dow — e.g. <code>0 2 * * *</code> = daily at 2am</small>
          </div>

          <div className="form-row">
            <label>Working Directory</label>
            <input value={form.working_directory} onChange={e => set('working_directory', e.target.value)} placeholder="/path/to/dir" />
          </div>

          <div className="form-row-inline">
            <div className="form-row">
              <label>Shell</label>
              <select value={form.shell_type} onChange={e => set('shell_type', e.target.value)}>
                {SHELL_OPTIONS.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div className="form-row">
              <label>Timeout (s)</label>
              <input type="number" min={0} value={form.timeout_seconds} onChange={e => set('timeout_seconds', Number(e.target.value))} />
            </div>
          </div>

          <div className="form-row-inline">
            <div className="form-row">
              <label>Max Retries</label>
              <input type="number" min={0} max={10} value={form.max_retries} onChange={e => set('max_retries', Number(e.target.value))} />
            </div>
            <div className="form-row">
              <label>Retry Delay (s)</label>
              <input type="number" min={1} value={form.retry_delay_seconds} onChange={e => set('retry_delay_seconds', Number(e.target.value))} />
            </div>
          </div>

          <div className="form-row-checkboxes">
            <label className="checkbox-label">
              <input type="checkbox" checked={form.allow_concurrent} onChange={e => set('allow_concurrent', e.target.checked)} />
              Allow concurrent runs
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={form.is_enabled} onChange={e => set('is_enabled', e.target.checked)} />
              Enabled
            </label>
          </div>

          <div className="form-row">
            <label>Environment Variables</label>
            {envRows.map((row, i) => (
              <div key={i} className="env-row">
                <input
                  placeholder="KEY"
                  value={row.key}
                  onChange={e => setEnvRows(rows => rows.map((r, j) => j === i ? { ...r, key: e.target.value } : r))}
                  className="font-mono env-key"
                />
                <span>=</span>
                <input
                  placeholder="value"
                  value={row.value}
                  onChange={e => setEnvRows(rows => rows.map((r, j) => j === i ? { ...r, value: e.target.value } : r))}
                  className="font-mono env-val"
                />
                <button type="button" className="btn-icon-danger" onClick={() => setEnvRows(rows => rows.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button type="button" className="btn-secondary btn-sm" onClick={() => setEnvRows(rows => [...rows, { key: '', value: '' }])}>
              + Add Variable
            </button>
          </div>

          <div className="form-actions">
            <button type="button" className="btn-secondary" onClick={onCancel}>Cancel</button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : initial ? 'Update Job' : 'Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

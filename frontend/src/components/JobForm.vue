<template>
  <div class="modal-backdrop" @click="cancelFn()">
    <div class="modal-box" @click.stop>
      <h2 class="modal-title">{{ initial ? 'Edit Job' : 'New Job' }}</h2>
      <form @submit.prevent="handleSubmit" class="form">
        <div v-if="error" class="form-error">{{ error }}</div>

        <div class="form-row">
          <label>Name *</label>
          <input required v-model="form.name" placeholder="My Backup Job" />
        </div>

        <div class="form-row">
          <label>Description</label>
          <input v-model="form.description" placeholder="Optional description" />
        </div>

        <div class="form-row">
          <label>Command *</label>
          <input required v-model="form.command" placeholder="python script.py" class="font-mono" />
        </div>

        <div class="form-row">
          <label>
            Cron Expression *
            <span class="cron-hint">{{ cronDescription }}</span>
          </label>
          <input required v-model="form.cron_expression" placeholder="* * * * *" class="font-mono" />
          <small class="field-hint">min hour dom month dow — e.g. <code>0 2 * * *</code> = daily at 2am</small>
        </div>

        <div class="form-row">
          <label class="checkbox-label" style="margin-bottom: 0.5rem">
            <input type="checkbox" v-model="useZip" @change="handleZipToggle" />
            Upload script package (ZIP)
          </label>

          <div v-if="useZip" class="zip-upload-area">
            <div v-if="initial && initial.package_name && !zipFile" class="zip-current">
              <span class="badge badge-neutral">Current package:</span>
              <code>{{ initial.package_name }}</code>
              <small class="field-hint">Select a new ZIP below to replace it</small>
            </div>
            <input
              ref="fileInputRef"
              type="file"
              accept=".zip"
              @change="handleFileChange"
              class="zip-file-input"
            />
            <small v-if="zipFile" class="field-hint">
              Selected: <strong>{{ zipFile.name }}</strong> ({{ (zipFile.size / 1024).toFixed(1) }} KB) — will be extracted as the working directory
            </small>
            <small v-else-if="!initial || !initial.package_name" class="field-hint">
              ZIP contents will be extracted to a dedicated directory used as the working directory for this job
            </small>
          </div>
          <input v-else v-model="form.working_directory" placeholder="/path/to/dir" />
        </div>

        <div class="form-row-inline">
          <div class="form-row">
            <label>Shell</label>
            <select v-model="form.shell_type">
              <option v-for="s in SHELL_OPTIONS" :key="s">{{ s }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>Timeout (s)</label>
            <input type="number" min="0" v-model.number="form.timeout_seconds" />
          </div>
        </div>

        <div class="form-row-inline">
          <div class="form-row">
            <label>Max Retries</label>
            <input type="number" min="0" max="10" v-model.number="form.max_retries" />
          </div>
          <div class="form-row">
            <label>Retry Delay (s)</label>
            <input type="number" min="1" v-model.number="form.retry_delay_seconds" />
          </div>
        </div>

        <div class="form-row-checkboxes">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.allow_concurrent" />
            Allow concurrent runs
          </label>
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.is_enabled" />
            Enabled
          </label>
        </div>

        <div class="form-row">
          <label>Environment Variables</label>
          <div v-for="(row, i) in envRows" :key="i" class="env-row">
            <input placeholder="KEY" v-model="row.key" class="font-mono env-key" />
            <span>=</span>
            <input placeholder="value" v-model="row.value" class="font-mono env-val" />
            <button type="button" class="btn-icon-danger" @click="envRows.splice(i, 1)">&#10005;</button>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="envRows.push({ key: '', value: '' })">
            + Add Variable
          </button>
        </div>

        <div class="form-actions">
          <button type="button" class="btn-secondary" @click="cancelFn()">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? (zipFile ? 'Uploading...' : 'Saving...') : initial ? 'Update Job' : 'Create Job' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'

const props = defineProps({
  initial: { type: Object, default: null },
  submitFn: { type: Function, required: true },
  cancelFn: { type: Function, required: true },
})

const SHELL_OPTIONS = ['auto', 'cmd', 'powershell', 'bash', 'sh']

const form = reactive(props.initial ? {
  name: props.initial.name,
  description: props.initial.description,
  command: props.initial.command,
  cron_expression: props.initial.cron_expression,
  working_directory: props.initial.working_directory,
  shell_type: props.initial.shell_type,
  timeout_seconds: props.initial.timeout_seconds,
  max_retries: props.initial.max_retries,
  retry_delay_seconds: props.initial.retry_delay_seconds,
  allow_concurrent: props.initial.allow_concurrent,
  is_enabled: props.initial.is_enabled,
} : {
  name: '',
  description: '',
  command: '',
  cron_expression: '* * * * *',
  working_directory: '',
  shell_type: 'auto',
  timeout_seconds: 3600,
  max_retries: 0,
  retry_delay_seconds: 60,
  allow_concurrent: false,
  is_enabled: true,
})

const envRows = reactive(
  props.initial
    ? Object.entries(props.initial.environment_vars || {}).map(function(e) { return { key: e[0], value: e[1] } })
    : []
)

const loading = ref(false)
const error = ref('')
const useZip = ref(!!(props.initial && props.initial.package_name))
const zipFile = ref(null)
const fileInputRef = ref(null)

function describeCron(expr) {
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return 'Invalid expression (need 5 fields)'
  const min = parts[0], hour = parts[1], dom = parts[2], mon = parts[3], dow = parts[4]
  if (expr === '* * * * *') return 'Every minute'
  if (min === '0' && hour === '*') return 'Every hour at :00'
  if (min !== '*' && hour !== '*' && dom === '*' && mon === '*' && dow === '*')
    return `Daily at ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`
  return `${min} ${hour} ${dom} ${mon} ${dow}`
}

const cronDescription = computed(() => describeCron(form.cron_expression))

function handleZipToggle() {
  if (!useZip.value) {
    zipFile.value = null
    if (fileInputRef.value) fileInputRef.value.value = ''
  }
}

function handleFileChange(e) {
  const f = e.target.files && e.target.files[0]
  if (f && !f.name.toLowerCase().endsWith('.zip')) {
    error.value = 'Please select a ZIP file'
    e.target.value = ''
    zipFile.value = null
    return
  }
  error.value = ''
  zipFile.value = f || null
}

async function handleSubmit() {
  error.value = ''
  if (useZip.value && !zipFile.value && !(props.initial && props.initial.package_name)) {
    error.value = 'Please select a ZIP file to upload'
    return
  }
  const env = {}
  for (var i = 0; i < envRows.length; i++) {
    var row = envRows[i]
    if (row.key.trim()) env[row.key.trim()] = row.value
  }
  try {
    loading.value = true
    await props.submitFn(
      Object.assign({}, form, { environment_vars: env }),
      useZip.value ? (zipFile.value || undefined) : undefined
    )
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}
</script>

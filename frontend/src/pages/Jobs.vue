<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">Jobs</h1>
      <button class="btn-primary" @click="showForm = true">+ New Job</button>
    </div>

    <div class="toolbar">
      <input
        class="search-input"
        placeholder="Search jobs..."
        v-model="search"
        @input="page = 1"
      />
      <span class="toolbar-count">{{ data ? data.total : 0 }} jobs</span>
    </div>

    <p v-if="loading" class="loading-text">Loading...</p>
    <div v-else class="table-container">
      <table class="table">
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
          <template v-for="job in items" :key="job.id">
            <tr :class="['job-row', !job.is_enabled ? 'job-disabled' : '']">
              <td>
                <button class="btn-link job-name" @click="toggleExpand(job.id)">{{ job.name }}</button>
                <div v-if="job.description" class="job-desc">{{ job.description }}</div>
              </td>
              <td class="font-mono text-sm">{{ job.cron_expression }}</td>
              <td>
                <StatusBadge :status="job.last_status" :is-running="job.is_running" />
                <span v-if="!job.is_enabled" class="badge badge-neutral ml-1">Paused</span>
              </td>
              <td class="text-sm text-muted">
                {{ job.last_run_at ? new Date(job.last_run_at).toLocaleString() : '—' }}
              </td>
              <td class="text-sm text-muted">
                {{ job.next_run_at ? new Date(job.next_run_at).toLocaleString() : '—' }}
              </td>
              <td>
                <div class="action-buttons">
                  <button
                    class="btn-action btn-run"
                    title="Run Now"
                    :disabled="!job.is_enabled || running"
                    @click="handleRun(job.id)"
                  >&#9654;</button>
                  <button
                    class="btn-action"
                    :title="job.is_enabled ? 'Pause' : 'Resume'"
                    @click="job.is_enabled ? handlePause(job.id) : handleResume(job.id)"
                  >{{ job.is_enabled ? '⏸' : '▶▶' }}</button>
                  <button class="btn-action" title="Edit" @click="editJob = job">&#9999;</button>
                  <button class="btn-action btn-delete" title="Delete" @click="deleteTarget = job">&#128465;</button>
                </div>
              </td>
            </tr>
            <tr v-if="expandedJob === job.id" :key="`${job.id}-exp`" class="expanded-row">
              <td colspan="6">
                <div class="expanded-content">
                  <div class="expanded-meta">
                    <strong>Command:</strong> <code>{{ job.command }}</code>
                    <template v-if="job.package_name"><strong>Package:</strong> <code>{{ job.package_name }}</code></template>
                    <template v-if="job.working_directory"><strong>CWD:</strong> <code>{{ job.working_directory }}</code></template>
                    <strong>Shell:</strong> {{ job.shell_type }}
                    <strong>Timeout:</strong> {{ job.timeout_seconds }}s
                    <strong>Retries:</strong> {{ job.max_retries }}
                  </div>
                  <div class="expanded-execs">
                    <strong>Recent executions:</strong>
                    <div v-for="exec in jobExecItems" :key="exec.id" class="mini-exec-row">
                      <StatusBadge :status="exec.status" :is-running="exec.status === 'running'" />
                      <span>{{ new Date(exec.started_at).toLocaleString() }}</span>
                      <span>{{ exec.duration_ms !== null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '...' }}</span>
                      <button class="btn-link" @click="selectedExec = exec.id">Logs</button>
                    </div>
                    <span v-if="!jobExecItems.length" class="text-muted">No executions yet</span>
                  </div>
                </div>
              </td>
            </tr>
          </template>
          <tr v-if="!items.length">
            <td colspan="6" class="table-empty">No jobs found. Create your first job!</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="page === 1" @click="page--" class="btn-secondary btn-sm">Prev</button>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="page++" class="btn-secondary btn-sm">Next</button>
    </div>

    <JobForm
      v-if="showForm || editJob"
      :initial="editJob"
      :submit-fn="handleFormSubmit"
      :cancel-fn="handleFormCancel"
    />

    <ConfirmDialog
      v-if="deleteTarget"
      :message="`Delete job &quot;${deleteTarget.name}&quot; and all its execution history?`"
      @confirm="handleDelete"
      @cancel="deleteTarget = null"
    />

    <ExecutionLog v-if="selectedExec" :exec-id="selectedExec" @close="selectedExec = null" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import {
  getJobs, createJob, updateJob, deleteJob,
  runJobNow, pauseJob, resumeJob, uploadJobPackage,
} from '../api/jobs'
import { getExecutions } from '../api/executions'
import { onSSEUpdate } from '../sseEvents'
import StatusBadge from '../components/StatusBadge.vue'
import JobForm from '../components/JobForm.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import ExecutionLog from '../components/ExecutionLog.vue'

const data = ref(null)
const loading = ref(false)
const page = ref(1)
const search = ref('')
const showForm = ref(false)
const editJob = ref(null)
const deleteTarget = ref(null)
const selectedExec = ref(null)
const expandedJob = ref(null)
const jobExecs = ref(null)
const running = ref(false)

const items = computed(() => (data.value && data.value.items) || [])
const jobExecItems = computed(() => (jobExecs.value && jobExecs.value.items) || [])
const totalPages = computed(() => data.value ? Math.ceil(data.value.total / 20) : 1)

async function fetchJobs() {
  loading.value = true
  try {
    data.value = await getJobs({
      page: page.value,
      page_size: 20,
      search: search.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

async function fetchJobExecs(jobId) {
  jobExecs.value = await getExecutions({ job_id: jobId, page_size: 5 }).catch(() => null)
}

// Batch page+search changes into a single fetch
watch([page, search], fetchJobs)

watch(expandedJob, (id) => { if (id) fetchJobExecs(id) })

function toggleExpand(id) {
  expandedJob.value = expandedJob.value === id ? null : id
}

async function invalidate() {
  await fetchJobs()
  if (expandedJob.value) fetchJobExecs(expandedJob.value)
}

async function handleRun(id) {
  running.value = true
  try { await runJobNow(id) } finally { running.value = false }
  await invalidate()
}

async function handlePause(id) { await pauseJob(id); await invalidate() }
async function handleResume(id) { await resumeJob(id); await invalidate() }

async function handleDelete() {
  await deleteJob(deleteTarget.value.id)
  deleteTarget.value = null
  await invalidate()
}

async function handleFormSubmit(formData, zipFile) {
  if (editJob.value) {
    await updateJob(editJob.value.id, formData)
    if (zipFile) await uploadJobPackage(editJob.value.id, zipFile)
    editJob.value = null
  } else {
    const wasEnabled = formData.is_enabled
    const createData = zipFile ? Object.assign({}, formData, { is_enabled: false }) : formData
    const job = await createJob(createData)
    if (zipFile) {
      await uploadJobPackage(job.id, zipFile)
      if (wasEnabled) await resumeJob(job.id)
    }
    showForm.value = false
  }
  await invalidate()
}

function handleFormCancel() {
  showForm.value = false
  editJob.value = null
}

let pollTimer = null
let unsubSSE = null

onMounted(() => {
  fetchJobs()
  pollTimer = setInterval(fetchJobs, 15000)
  unsubSSE = onSSEUpdate(fetchJobs)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (unsubSSE) unsubSSE()
})
</script>

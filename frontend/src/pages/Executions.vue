<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">Execution History</h1>
    </div>

    <div class="toolbar">
      <select class="filter-select" v-model="status" @change="page = 1">
        <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ s || 'All statuses' }}</option>
      </select>
      <span class="toolbar-count">{{ data ? data.total : 0 }} executions</span>
    </div>

    <p v-if="loading" class="loading-text">Loading...</p>
    <div v-else class="table-container">
      <table class="table">
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
          <tr v-for="exec in items" :key="exec.id">
            <td>{{ exec.job_name || exec.job_id }}</td>
            <td><StatusBadge :status="exec.status" :is-running="exec.status === 'running'" /></td>
            <td>{{ exec.triggered_by }}{{ exec.retry_number > 0 ? ` (retry #${exec.retry_number})` : '' }}</td>
            <td class="font-mono">{{ exec.exit_code != null ? exec.exit_code : '—' }}</td>
            <td class="text-sm">{{ new Date(exec.started_at).toLocaleString() }}</td>
            <td class="text-sm">{{ exec.duration_ms !== null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '...' }}</td>
            <td><button class="btn-link" @click="selectedExec = exec.id">Logs</button></td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="7" class="table-empty">No executions found</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="page === 1" @click="page--" class="btn-secondary btn-sm">Prev</button>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="page++" class="btn-secondary btn-sm">Next</button>
    </div>

    <ExecutionLog v-if="selectedExec" :exec-id="selectedExec" @close="selectedExec = null" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { getExecutions } from '../api/executions'
import { onSSEUpdate } from '../sseEvents'
import StatusBadge from '../components/StatusBadge.vue'
import ExecutionLog from '../components/ExecutionLog.vue'

const STATUS_OPTIONS = ['', 'running', 'success', 'failed', 'timeout', 'killed']

const data = ref(null)
const loading = ref(false)
const page = ref(1)
const status = ref('')
const selectedExec = ref(null)

const items = computed(() => (data.value && data.value.items) || [])
const totalPages = computed(() => data.value ? Math.ceil(data.value.total / 30) : 1)

async function fetchExecutions() {
  loading.value = true
  try {
    data.value = await getExecutions({
      page: page.value,
      page_size: 30,
      status: status.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

watch([page, status], fetchExecutions)

let pollTimer = null
let unsubSSE = null

onMounted(() => {
  fetchExecutions()
  pollTimer = setInterval(fetchExecutions, 10000)
  unsubSSE = onSSEUpdate(fetchExecutions)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (unsubSSE) unsubSSE()
})
</script>

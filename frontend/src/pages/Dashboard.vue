<template>
  <div class="page">
    <h1 class="page-title">Dashboard</h1>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats ? stats.total_jobs : '—' }}</div>
        <div class="stat-label">Total Jobs</div>
      </div>
      <div class="stat-card stat-card-green">
        <div class="stat-value">{{ stats ? stats.enabled_jobs : '—' }}</div>
        <div class="stat-label">Enabled</div>
      </div>
      <div class="stat-card stat-card-blue">
        <div class="stat-value">{{ stats ? stats.running_jobs : '—' }}</div>
        <div class="stat-label">Running Now</div>
      </div>
      <div class="stat-card stat-card-green">
        <div class="stat-value">{{ stats ? stats.success_24h : '—' }}</div>
        <div class="stat-label">Success (24h)</div>
      </div>
      <div class="stat-card stat-card-red">
        <div class="stat-value">{{ stats ? stats.failed_24h : '—' }}</div>
        <div class="stat-label">Failed (24h)</div>
      </div>
      <div v-if="successRate !== null" class="stat-card">
        <div class="stat-value">{{ successRate }}%</div>
        <div class="stat-label">Success Rate (24h)</div>
      </div>
    </div>

    <h2 class="section-title">Recent Executions</h2>
    <div class="table-container">
      <table class="table">
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
          <tr v-for="exec in recentItems" :key="exec.id">
            <td>{{ exec.job_name }}</td>
            <td><StatusBadge :status="exec.status" :is-running="exec.status === 'running'" /></td>
            <td>{{ exec.triggered_by }}</td>
            <td>{{ new Date(exec.started_at).toLocaleString() }}</td>
            <td>{{ exec.duration_ms !== null ? `${(exec.duration_ms / 1000).toFixed(1)}s` : '—' }}</td>
            <td><button class="btn-link" @click="selectedExec = exec.id">Logs</button></td>
          </tr>
          <tr v-if="!recentItems.length">
            <td colspan="6" class="table-empty">No executions yet</td>
          </tr>
        </tbody>
      </table>
    </div>

    <ExecutionLog v-if="selectedExec" :exec-id="selectedExec" @close="selectedExec = null" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getStats, getExecutions } from '../api/executions'
import { onSSEUpdate } from '../sseEvents'
import StatusBadge from '../components/StatusBadge.vue'
import ExecutionLog from '../components/ExecutionLog.vue'

const stats = ref(null)
const recent = ref(null)
const selectedExec = ref(null)

const recentItems = computed(() => (recent.value && recent.value.items) || [])

const successRate = computed(() => {
  if (!stats.value || stats.value.executions_24h === 0) return null
  return Math.round((stats.value.success_24h / stats.value.executions_24h) * 100)
})

async function fetchAll() {
  const results = await Promise.all([
    getStats().catch(() => null),
    getExecutions({ page_size: 10 }).catch(() => null),
  ])
  stats.value = results[0]
  recent.value = results[1]
}

let pollTimer = null
let unsubSSE = null

onMounted(() => {
  fetchAll()
  pollTimer = setInterval(fetchAll, 10000)
  unsubSSE = onSSEUpdate(fetchAll)
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (unsubSSE) unsubSSE()
})
</script>

<template>
  <div class="modal-backdrop" @click="$emit('close')">
    <div class="modal-box modal-box-lg" @click.stop>
      <div class="log-header">
        <h2 class="modal-title">Execution Log</h2>
        <button class="btn-icon" @click="$emit('close')">&#10005;</button>
      </div>

      <p v-if="loading" class="loading-text">Loading...</p>

      <template v-else-if="exec">
        <div class="log-meta">
          <StatusBadge :status="exec.status" :is-running="exec.status === 'running'" />
          <span>PID: {{ exec.pid != null ? exec.pid : '—' }}</span>
          <span>Exit: {{ exec.exit_code != null ? exec.exit_code : '—' }}</span>
          <span>Duration: {{ formatDuration(exec.duration_ms) }}</span>
          <span>Trigger: {{ exec.triggered_by }}</span>
          <span v-if="exec.retry_number > 0">Retry #{{ exec.retry_number }}</span>
          <button v-if="exec.status === 'running'" class="btn-danger btn-sm" @click="handleKill">Kill</button>
        </div>
        <div class="log-meta-time">
          <span>Started: {{ new Date(exec.started_at).toLocaleString() }}</span>
          <span v-if="exec.finished_at">Finished: {{ new Date(exec.finished_at).toLocaleString() }}</span>
        </div>

        <div class="log-tabs">
          <button :class="['log-tab', tab === 'stdout' ? 'active' : '']" @click="tab = 'stdout'">stdout</button>
          <button :class="['log-tab', tab === 'stderr' ? 'active' : '']" @click="tab = 'stderr'">
            stderr {{ exec.stderr ? '(!)' : '' }}
          </button>
        </div>
        <pre class="log-output"><template v-if="tab === 'stdout'"><span v-if="exec.stdout">{{ exec.stdout }}</span><span v-else class="log-empty">(empty)</span></template><template v-else><span v-if="exec.stderr">{{ exec.stderr }}</span><span v-else class="log-empty">(empty)</span></template></pre>
      </template>

      <p v-else>Not found</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getExecution, killExecution } from '../api/executions'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({ execId: String })
defineEmits(['close'])

const exec = ref(null)
const loading = ref(true)
const tab = ref('stdout')
let pollTimer = null

function formatDuration(ms) {
  if (ms === null || ms === undefined) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const m = Math.floor(ms / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  return `${m}m ${s}s`
}

async function fetchExec() {
  if (pollTimer) { clearTimeout(pollTimer); pollTimer = null }
  try {
    exec.value = await getExecution(props.execId)
  } catch {
    exec.value = null
  } finally {
    loading.value = false
  }
  if (exec.value && exec.value.status === 'running') {
    pollTimer = setTimeout(fetchExec, 2000)
  }
}

async function handleKill() {
  await killExecution(props.execId)
  fetchExec()
}

onMounted(fetchExec)
onUnmounted(() => { if (pollTimer) clearTimeout(pollTimer) })
</script>

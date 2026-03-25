<template>
  <span :class="`badge ${cfg.className}`">{{ cfg.label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: null },
  isRunning: { type: Boolean, default: false },
})

const statusConfig = {
  success: { label: 'Success', className: 'badge-success' },
  failed:  { label: 'Failed',  className: 'badge-error' },
  timeout: { label: 'Timeout', className: 'badge-warning' },
  killed:  { label: 'Killed',  className: 'badge-warning' },
  running: { label: 'Running', className: 'badge-running' },
}

const cfg = computed(() => {
  const key = props.isRunning ? 'running' : (props.status || 'unknown')
  return statusConfig[key] || { label: key, className: 'badge-neutral' }
})
</script>

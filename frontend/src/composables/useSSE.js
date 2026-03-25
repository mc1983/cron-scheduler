import { onMounted, onUnmounted } from 'vue'
import { emitSSEUpdate } from '../sseEvents'

export function useSSE() {
  let es = null
  let reconnectTimer = null

  function connect() {
    es = new EventSource('/api/v1/events')

    es.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        if (event.type === 'execution_started' || event.type === 'execution_finished') {
          emitSSEUpdate()
        }
      } catch {
        // ignore parse errors
      }
    }

    es.onerror = () => {
      es.close()
      reconnectTimer = setTimeout(connect, 5000)
    }
  }

  onMounted(connect)

  onUnmounted(() => {
    if (es) es.close()
    if (reconnectTimer) clearTimeout(reconnectTimer)
  })
}

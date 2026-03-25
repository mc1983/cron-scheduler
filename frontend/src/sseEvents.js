// Simple pub/sub for SSE events — lets any component subscribe to live updates.
const listeners = new Set()

export function onSSEUpdate(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export function emitSSEUpdate() {
  listeners.forEach(fn => fn())
}

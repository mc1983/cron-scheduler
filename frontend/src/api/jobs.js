import client from './client'

export const getJobs = async (params) => {
  const { data } = await client.get('/jobs', { params })
  return data
}

export const getJob = async (id) => {
  const { data } = await client.get(`/jobs/${id}`)
  return data
}

export const createJob = async (payload) => {
  const { data } = await client.post('/jobs', payload)
  return data
}

export const updateJob = async (id, payload) => {
  const { data } = await client.put(`/jobs/${id}`, payload)
  return data
}

export const deleteJob = async (id) => {
  await client.delete(`/jobs/${id}`)
}

export const runJobNow = async (id) => {
  await client.post(`/jobs/${id}/run`)
}

export const pauseJob = async (id) => {
  const { data } = await client.post(`/jobs/${id}/pause`)
  return data
}

export const resumeJob = async (id) => {
  const { data } = await client.post(`/jobs/${id}/resume`)
  return data
}

export const uploadJobPackage = async (id, file) => {
  const formData = new FormData()
  formData.append('file', file)
  // Use fetch (not axios) so the browser sets the multipart boundary correctly.
  const res = await fetch(`/api/v1/jobs/${id}/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    const json = await res.json().catch(() => null)
    const detail = json && json.detail
    const msg = detail
      ? (typeof detail === 'string' ? detail : JSON.stringify(detail))
      : `HTTP ${res.status}`
    throw new Error(msg)
  }
  return res.json()
}

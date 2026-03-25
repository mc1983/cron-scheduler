import client from './client'

export const getExecutions = async (params) => {
  const { data } = await client.get('/executions', { params })
  return data
}

export const getExecution = async (id) => {
  const { data } = await client.get(`/executions/${id}`)
  return data
}

export const killExecution = async (id) => {
  await client.post(`/executions/${id}/kill`)
}

export const deleteExecution = async (id) => {
  await client.delete(`/executions/${id}`)
}

export const getStats = async () => {
  const { data } = await client.get('/stats')
  return data
}

import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
})

client.interceptors.response.use(
  res => res,
  err => {
    const detail = err.response && err.response.data && err.response.data.detail
    if (detail) {
      const msg = typeof detail === 'string' ? detail : JSON.stringify(detail)
      return Promise.reject(new Error(msg))
    }
    return Promise.reject(err)
  }
)

export default client

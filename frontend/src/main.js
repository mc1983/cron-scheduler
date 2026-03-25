import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import Dashboard from './pages/Dashboard.vue'
import Jobs from './pages/Jobs.vue'
import Executions from './pages/Executions.vue'
import './styles.css'

const router = createRouter({
  history: createWebHistory(),
  linkActiveClass: 'active',
  linkExactActiveClass: 'active',
  routes: [
    { path: '/', component: Dashboard },
    { path: '/jobs', component: Jobs },
    { path: '/executions', component: Executions },
  ],
})

const app = createApp(App)
app.use(router)
app.mount('#app')

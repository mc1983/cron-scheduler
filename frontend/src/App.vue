<template>
  <div class="app">
    <nav class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">&#9201;</span>
        <span class="brand-name">CronScheduler</span>
      </div>
      <RouterLink to="/" class="nav-link">Dashboard</RouterLink>
      <RouterLink to="/jobs" class="nav-link">Jobs</RouterLink>
      <RouterLink to="/executions" class="nav-link">Executions</RouterLink>
      <div class="sidebar-footer">
        <a href="/api/v1/docs" target="_blank" rel="noopener" class="nav-link nav-link-muted">
          API Docs &#8599;
        </a>
      </div>
    </nav>
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { useSSE } from './composables/useSSE'
useSSE()
</script>

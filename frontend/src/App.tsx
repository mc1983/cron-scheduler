import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Dashboard } from './pages/Dashboard';
import { Jobs } from './pages/Jobs';
import { Executions } from './pages/Executions';
import { useSSE } from './hooks/useSSE';
import './styles.css';

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 15000, retry: 1 } },
});

function AppContent() {
  useSSE();
  return (
    <div className="app">
      <nav className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-icon">⏱</span>
          <span className="brand-name">CronScheduler</span>
        </div>
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Dashboard
        </NavLink>
        <NavLink to="/jobs" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Jobs
        </NavLink>
        <NavLink to="/executions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Executions
        </NavLink>
        <div className="sidebar-footer">
          <a href="/api/v1/docs" target="_blank" rel="noopener" className="nav-link nav-link-muted">
            API Docs ↗
          </a>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/executions" element={<Executions />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

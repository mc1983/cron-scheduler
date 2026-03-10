import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// index.css intentionally unused — styles.css is imported in App.tsx
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Paper Trail frontend. In dev, VITE_API_BASE (see .env.example) points at
// the FastAPI backend (uvicorn on :8010).
export default defineConfig({
  plugins: [react()],
})

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { isSupabaseConfigured, supabase } from './lib/supabaseClient'
import './index.css'
import App from './App.tsx'
import { useAuthStore } from './store/useAuthStore'

void useAuthStore.getState().initFromSession()

if (isSupabaseConfigured) {
  supabase.auth.onAuthStateChange((event, session) => {
    // Startup calls initFromSession() before the magic-link hash/query is applied,
    // so getSession() can be null on the first run. Supabase then emits
    // INITIAL_SESSION with a session — we must hydrate then or the UI stays in guest mode.
    if (event === 'INITIAL_SESSION' && !session) return
    void useAuthStore.getState().initFromSession()
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

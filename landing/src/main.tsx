import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import Privacidad from './Privacidad';
import { initPostHog } from './lib/posthog';
import './index.css';

// Inicializa PostHog solo si YA hay consentimiento previo (no en la 1ª visita).
initPostHog();

// Ruteo mínimo: / (landing) y /privacidad. Sin router pesado.
const path = window.location.pathname;
const Page = path.startsWith('/privacidad') ? Privacidad : App;

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Page />
  </React.StrictMode>
);

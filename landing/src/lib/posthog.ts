import type { PostHog } from 'posthog-js';

/**
 * PostHog SOLO en la landing y SOLO tras consentimiento (Ley 29733).
 * Nada se envía antes de que el usuario acepte en el banner.
 * posthog-js se carga con import() dinámico para no pesar en el bundle
 * crítico (mejor LCP): solo entra cuando hay consentimiento.
 */
const KEY = import.meta.env.VITE_POSTHOG_KEY as string | undefined;
const HOST = (import.meta.env.VITE_POSTHOG_HOST as string) || 'https://us.i.posthog.com';
const CONSENT_KEY = 'sg_consent';

let ph: PostHog | null = null;
let loading = false;

export function hasConsent(): boolean {
  return localStorage.getItem(CONSENT_KEY) === 'granted';
}
export function consentDecided(): boolean {
  const v = localStorage.getItem(CONSENT_KEY);
  return v === 'granted' || v === 'denied';
}

export async function initPostHog() {
  if (ph || loading || !KEY || !hasConsent()) return;
  loading = true;
  const mod = await import('posthog-js');
  const posthog = mod.default;
  posthog.init(KEY, {
    api_host: HOST,
    person_profiles: 'identified_only',
    autocapture: true,
    capture_pageview: true,
    capture_pageleave: true,
    session_recording: {
      maskAllInputs: true, // enmascara TODOS los inputs en el replay
      maskTextSelector: '[data-ph-mask]',
    },
    enable_heatmaps: true,
  });
  ph = posthog;
}

export function grantConsent() {
  localStorage.setItem(CONSENT_KEY, 'granted');
  void initPostHog();
}
export function denyConsent() {
  localStorage.setItem(CONSENT_KEY, 'denied');
}

// no-op seguro si PostHog aún no cargó (sin consentimiento)
export function track(event: string, props?: Record<string, unknown>) {
  ph?.capture(event, props);
}
export function identifyLead(leadId: number | string, props?: Record<string, unknown>) {
  ph?.identify(String(leadId), props);
}

// UTM + referrer: se leen una vez y se adjuntan al Lead.
export function getAttribution() {
  const p = new URLSearchParams(window.location.search);
  return {
    utm_source: p.get('utm_source') || '',
    utm_campaign: p.get('utm_campaign') || '',
    referrer: document.referrer || '',
  };
}

export interface LeadPayload {
  nombre: string;
  email: string;
  empresa: string;
  telefono?: string;
  rubro?: string;
  tamano?: string;
  usa_inventario?: boolean | null;
  mensaje?: string;
  website?: string; // honeypot
  utm_source?: string;
  utm_campaign?: string;
}

// Mismo origen en producción (rewrites de Vercel) → '/api/leads/'.
// En dev se puede apuntar al backend local con VITE_API_BASE.
const API_BASE = (import.meta.env.VITE_API_BASE as string) || '';

export async function submitLead(payload: LeadPayload): Promise<{ ok: boolean; id?: number; error?: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/leads/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.status === 429) return { ok: false, error: 'Demasiados intentos. Intenta más tarde.' };
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = typeof data === 'object' ? Object.values(data).flat().join(' ') : 'Error';
      return { ok: false, error: msg || 'No se pudo enviar. Revisa los datos.' };
    }
    return { ok: true, id: data.id };
  } catch {
    return { ok: false, error: 'Sin conexión. Intenta de nuevo.' };
  }
}

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { grantConsent, denyConsent, consentDecided } from '@/lib/posthog';

/**
 * Banner de consentimiento (Ley 29733). PostHog se inicializa SOLO al aceptar.
 * Si ya se decidió antes, no se muestra.
 */
export function ConsentBanner() {
  const [visible, setVisible] = useState(!consentDecided());
  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 border-t border-ink-700 bg-ink-900/95 backdrop-blur px-4 py-4 animate-fade-in">
      <div className="container flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-ink-200">
          Usamos analítica propia para entender cómo se usa esta página y mejorarla.
          Nada se activa hasta que aceptes.{' '}
          <a href="/privacidad" className="text-brand-300 underline underline-offset-2 hover:text-brand-200">
            Política de privacidad
          </a>.
        </p>
        <div className="flex shrink-0 gap-2">
          <Button variant="ghost" size="sm" onClick={() => { denyConsent(); setVisible(false); }}>
            Rechazar
          </Button>
          <Button variant="primary" size="sm" onClick={() => { grantConsent(); setVisible(false); }}>
            Aceptar
          </Button>
        </div>
      </div>
    </div>
  );
}

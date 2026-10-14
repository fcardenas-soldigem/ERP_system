import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { CheckCircle2 } from 'lucide-react';
import { submitLead, getAttribution } from '@/lib/leads';
import { track, identifyLead } from '@/lib/posthog';
import { RUBROS, TAMANOS } from '@/content';

export function LeadForm() {
  const [step, setStep] = useState<1 | 2>(1);
  const [done, setDone] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [started, setStarted] = useState(false);
  const [f, setF] = useState({
    nombre: '', email: '', empresa: '',
    rubro: '', tamano: '', usa_inventario: '' as '' | 'si' | 'no',
    website: '', // honeypot
  });

  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    if (!started) { setStarted(true); track('form_started'); }
    setF((p) => ({ ...p, [k]: e.target.value }));
  };
  const fieldDone = (k: string) => () => f[k as keyof typeof f] && track('form_field_completed', { field: k });

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError('');
    const attribution = getAttribution();
    const res = await submitLead({
      nombre: f.nombre.trim(), email: f.email.trim(), empresa: f.empresa.trim(),
      rubro: f.rubro, tamano: f.tamano,
      usa_inventario: f.usa_inventario === '' ? null : f.usa_inventario === 'si',
      website: f.website,
      utm_source: attribution.utm_source,
      utm_campaign: attribution.utm_campaign,
      mensaje: attribution.referrer ? `ref: ${attribution.referrer}` : '',
    });
    setSending(false);
    if (res.ok) {
      if (res.id) identifyLead(res.id, { empresa: f.empresa, rubro: f.rubro });
      track('form_submitted', { rubro: f.rubro, tamano: f.tamano });
      setDone(true);
    } else {
      setError(res.error || 'No se pudo enviar.');
      track('form_error', { message: res.error });
    }
  }

  if (done) {
    return (
      <div className="rounded-lg border border-success/30 bg-success/10 p-6 text-center" role="status">
        <CheckCircle2 className="mx-auto mb-3 size-10 text-success-500" />
        <h3 className="text-lg font-semibold text-white">Listo, quedaste en la lista</h3>
        <p className="mt-1 text-sm text-ink-200">
          Te escribimos a <span className="font-medium text-white" data-ph-mask>{f.email}</span> apenas
          abramos tu acceso. Gracias por sumarte.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={enviar} className="space-y-4" noValidate>
      {/* Honeypot: oculto para humanos, tentador para bots */}
      <div aria-hidden className="absolute left-[-9999px] h-0 w-0 overflow-hidden">
        <label>No llenar
          <input tabIndex={-1} autoComplete="off" value={f.website}
                 onChange={set('website')} />
        </label>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="nombre">Nombre</Label>
        <Input id="nombre" required value={f.nombre} onChange={set('nombre')}
               onBlur={fieldDone('nombre')} placeholder="Tu nombre" data-ph-mask />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="email">Email de trabajo</Label>
        <Input id="email" type="email" required value={f.email} onChange={set('email')}
               onBlur={fieldDone('email')} placeholder="tu@empresa.pe" data-ph-mask />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="empresa">Empresa</Label>
        <Input id="empresa" required value={f.empresa} onChange={set('empresa')}
               onBlur={fieldDone('empresa')} placeholder="Nombre de tu empresa" data-ph-mask />
      </div>

      {step === 2 && (
        <div className="grid gap-4 border-t border-ink-700 pt-4 animate-fade-up">
          <div className="space-y-1.5">
            <Label htmlFor="rubro">Rubro <span className="text-ink-400">(opcional)</span></Label>
            <Select id="rubro" value={f.rubro} onChange={set('rubro')} onBlur={fieldDone('rubro')}>
              <option value="">Selecciona…</option>
              {RUBROS.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="tamano">Tamaño del equipo <span className="text-ink-400">(opcional)</span></Label>
            <Select id="tamano" value={f.tamano} onChange={set('tamano')} onBlur={fieldDone('tamano')}>
              <option value="">Selecciona…</option>
              {TAMANOS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="usa_inventario">¿Manejas inventario? <span className="text-ink-400">(opcional)</span></Label>
            <Select id="usa_inventario" value={f.usa_inventario} onChange={set('usa_inventario')} onBlur={fieldDone('usa_inventario')}>
              <option value="">Selecciona…</option>
              <option value="si">Sí, manejo stock</option>
              <option value="no">No, trabajo a pedido</option>
            </Select>
          </div>
        </div>
      )}

      {error && <p className="text-sm text-danger-500" role="alert">{error}</p>}

      <Button type="submit" variant="primary" size="lg" className="w-full" disabled={sending}>
        {sending ? 'Enviando…' : 'Solicitar acceso anticipado'}
      </Button>

      {step === 1 ? (
        <button type="button" onClick={() => setStep(2)}
                className="w-full text-center text-xs text-ink-300 hover:text-ink-100 transition-colors">
          Cuéntanos un poco más (opcional)
        </button>
      ) : (
        <p className="text-center text-xs text-ink-400">Solo tomará un momento. Nada de spam.</p>
      )}
    </form>
  );
}

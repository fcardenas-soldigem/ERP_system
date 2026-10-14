import { useEffect, useRef } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Section } from '@/components/Section';
import { LeadForm } from '@/components/LeadForm';
import { ConsentBanner } from '@/components/ConsentBanner';
import { FEATURES, COMING_SOON } from '@/content';
import { track } from '@/lib/posthog';

const ERP_LOGIN = '/login'; // vía rewrite de Vercel va al ERP

function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-800/80 bg-ink-950/80 backdrop-blur">
      <div className="container flex h-16 items-center justify-between">
        <a href="/" className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-brand-500 font-bold text-white">S</span>
          <span className="font-semibold text-white">Soldigem ERP</span>
        </a>
        <div className="flex items-center gap-2">
          <a href={ERP_LOGIN} onClick={() => track('cta_clicked', { cta: 'ingresar_nav' })}>
            <Button variant="ghost" size="sm">Ingresar</Button>
          </a>
          <a href="#acceso" onClick={() => track('cta_clicked', { cta: 'acceso_nav' })}>
            <Button variant="primary" size="sm">Solicitar acceso</Button>
          </a>
        </div>
      </div>
    </header>
  );
}

function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onPlay = () => track('video_played', { where: 'hero' });
    v.addEventListener('play', onPlay, { once: true });
    return () => v.removeEventListener('play', onPlay);
  }, []);

  return (
    <section className="relative overflow-hidden border-b border-ink-800">
      {/* Video loop de fondo (Higgsfield Wan 3.0). poster evita parpadeo y ayuda al LCP */}
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          autoPlay muted loop playsInline
          poster="/l-assets/hero-poster.jpg"
        >
          <source src="/media/hero.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-gradient-to-b from-ink-950/40 via-ink-950/70 to-ink-950" />
      </div>

      <div className="container relative grid gap-12 py-20 lg:grid-cols-2 lg:py-28">
        <div className="max-w-xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-ink-700 bg-ink-900/60 px-3 py-1 text-xs text-ink-200">
            <span className="size-1.5 rounded-full bg-brand-400" /> ERP para PYMEs peruanas que venden B2B
          </span>
          <h1 className="mt-5 text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl">
            El back-office B2B que se cierra solo
          </h1>
          <p className="mt-5 text-lg text-ink-200">
            De la cotización a la venta y las órdenes de compra por proveedor en un clic.
            Con el margen real de cada venta, multimoneda USD/PEN y el IGV listo para SUNAT.
            Funciona con o sin inventario.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#acceso" onClick={() => track('cta_clicked', { cta: 'acceso_hero' })}>
              <Button variant="primary" size="lg">Solicitar acceso anticipado <ArrowRight /></Button>
            </a>
            <a href={ERP_LOGIN} onClick={() => track('cta_clicked', { cta: 'ingresar_hero' })}>
              <Button variant="secondary" size="lg">Ya tengo cuenta</Button>
            </a>
          </div>
        </div>

        {/* Captura REAL del dashboard en marco de dispositivo */}
        <DeviceFrame
          src="/l-assets/shot-dashboard.png"
          alt="Dashboard de Soldigem ERP mostrando ventas del mes, cobrado y utilidad"
        />
      </div>
    </section>
  );
}

function DeviceFrame({ src, alt }: { src: string; alt: string }) {
  return (
    <button
      onClick={() => track('screenshot_zoomed', { shot: src })}
      className="group relative mx-auto w-full max-w-xl self-center rounded-xl border border-ink-700 bg-ink-800 p-2 shadow-2xl transition-transform duration-[160ms] ease-[cubic-bezier(0.23,1,0.32,1)] hover:scale-[1.01]"
      aria-label="Ampliar captura"
    >
      <div className="flex items-center gap-1.5 px-2 py-1.5">
        <span className="size-2.5 rounded-full bg-ink-600" />
        <span className="size-2.5 rounded-full bg-ink-600" />
        <span className="size-2.5 rounded-full bg-ink-600" />
      </div>
      <img src={src} alt={alt} loading="lazy" decoding="async"
           className="w-full rounded-lg border border-ink-700" />
    </button>
  );
}

function Features() {
  return (
    <Section name="features" id="producto" className="border-b border-ink-800 py-20">
      <div className="container">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold tracking-tight text-white">Todo lo que ya hace hoy</h2>
          <p className="mt-3 text-ink-200">Sin módulos a medias. Esto funciona en producción ahora mismo.</p>
        </div>
        <div className="mt-12 grid gap-px overflow-hidden rounded-xl border border-ink-800 bg-ink-800 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-ink-950 p-6">
              <f.icon className="size-5 text-brand-400" strokeWidth={1.75} />
              <h3 className="mt-4 font-semibold text-white">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-300">{f.body}</p>
            </div>
          ))}
        </div>
      </div>
    </Section>
  );
}

function Screenshots() {
  const shots = [
    { src: '/l-assets/shot-cotizacion.png', alt: 'Cotización con costo y proveedor por línea',
      cap: 'Costeas la cotización por línea; el margen aparece al instante.' },
    { src: '/l-assets/shot-finanzas.png', alt: 'Finanzas: IGV por pagar y crédito fiscal',
      cap: 'Tu IGV por pagar y tu crédito fiscal, calculados solos.' },
  ];
  return (
    <Section name="capturas" className="border-b border-ink-800 py-20">
      <div className="container grid gap-10 lg:grid-cols-2">
        {shots.map((s) => (
          <figure key={s.src}>
            <DeviceFrame src={s.src} alt={s.alt} />
            <figcaption className="mt-4 text-center text-sm text-ink-300">{s.cap}</figcaption>
          </figure>
        ))}
      </div>
    </Section>
  );
}

function ComingSoon() {
  return (
    <Section name="proximamente" className="border-b border-ink-800 py-20">
      <div className="container max-w-2xl text-center">
        <span className="text-xs font-semibold uppercase tracking-wider text-brand-400">Próximamente</span>
        <h2 className="mt-3 text-3xl font-bold tracking-tight text-white">Lo que estamos construyendo</h2>
        <ul className="mt-8 grid gap-3 text-left sm:grid-cols-3">
          {COMING_SOON.map((c) => (
            <li key={c} className="rounded-lg border border-ink-800 bg-ink-900 p-4 text-sm text-ink-200">
              {c}
            </li>
          ))}
        </ul>
      </div>
    </Section>
  );
}

function Acceso() {
  return (
    <Section name="acceso" id="acceso" className="py-20">
      <div className="container grid items-center gap-12 lg:grid-cols-2">
        <div className="max-w-md">
          <h2 className="text-3xl font-bold tracking-tight text-white">Pide tu acceso anticipado</h2>
          <p className="mt-4 text-ink-200">
            Estamos abriendo cupos para empresas B2B peruanas. Déjanos tus datos y te
            avisamos apenas tengamos lugar para ti.
          </p>
          <ul className="mt-6 space-y-2 text-sm text-ink-300">
            {['Sin tarjeta', 'Acompañamiento en la puesta en marcha', 'En español, hecho para Perú'].map((t) => (
              <li key={t} className="flex items-center gap-2"><Check className="size-4 text-success-500" /> {t}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl border border-ink-800 bg-ink-900 p-6 sm:p-8">
          <LeadForm />
        </div>
      </div>
    </Section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-ink-800 py-10">
      <div className="container flex flex-col items-center justify-between gap-4 text-sm text-ink-400 sm:flex-row">
        <span>© {new Date().getFullYear()} Soldigem. Hecho en Perú.</span>
        <div className="flex gap-6">
          <a href="/privacidad" className="hover:text-ink-100">Privacidad</a>
          <a href={ERP_LOGIN} className="hover:text-ink-100">Ingresar</a>
        </div>
      </div>
    </footer>
  );
}

export default function App() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Features />
        <Screenshots />
        <ComingSoon />
        <Acceso />
      </main>
      <Footer />
      <ConsentBanner />
    </>
  );
}

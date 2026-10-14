const UPDATED = 'octubre de 2026';

export default function Privacidad() {
  return (
    <main className="container max-w-2xl py-16">
      <a href="/" className="text-sm text-brand-300 hover:text-brand-200">&larr; Volver</a>
      <h1 className="mt-6 text-3xl font-bold text-white">Política de privacidad</h1>
      <p className="mt-2 text-sm text-ink-400">Actualizada en {UPDATED}</p>

      <div className="mt-8 space-y-6 text-sm leading-relaxed text-ink-200">
        <section>
          <h2 className="text-lg font-semibold text-white">Responsable del tratamiento</h2>
          <p className="mt-2">
            Soldigem (en adelante, "nosotros") es responsable del tratamiento de los datos
            personales que nos facilitas en esta página, conforme a la Ley N.º 29733, Ley de
            Protección de Datos Personales del Perú, y su reglamento.
          </p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-white">Qué datos recogemos y con qué finalidad</h2>
          <p className="mt-2">
            Cuando solicitas acceso anticipado recogemos tu nombre, email, empresa y, de forma
            opcional, rubro, tamaño del equipo y si manejas inventario. Los usamos únicamente
            para contactarte sobre el acceso al producto y entender la demanda. No vendemos ni
            cedemos tus datos a terceros con fines comerciales.
          </p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-white">Analítica y cookies</h2>
          <p className="mt-2">
            Usamos PostHog para analítica de uso (páginas vistas, mapas de calor, grabación de
            sesión con todos los campos de formulario enmascarados). Esta analítica se activa
            solo si aceptas en el banner de consentimiento; si la rechazas, no se envía ninguna
            información. Puedes cambiar tu decisión borrando los datos del sitio en tu navegador.
          </p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-white">Tus derechos (ARCO)</h2>
          <p className="mt-2">
            Puedes ejercer tus derechos de acceso, rectificación, cancelación y oposición sobre
            tus datos personales en cualquier momento, escribiéndonos al correo de contacto. Tu
            solicitud será atendida en los plazos que fija la Ley 29733.
          </p>
        </section>
        <section>
          <h2 className="text-lg font-semibold text-white">Contacto</h2>
          <p className="mt-2">
            Para ejercer tus derechos o resolver dudas sobre esta política, escríbenos a{' '}
            <a href="mailto:hola@soldigem.com.pe" className="text-brand-300 underline underline-offset-2">
              hola@soldigem.com.pe
            </a>.
          </p>
        </section>
      </div>
    </main>
  );
}

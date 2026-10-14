import { useEffect, useRef } from 'react';
import { track } from '@/lib/posthog';

/**
 * Reveal al entrar en viewport + evento section_viewed (una vez) y
 * section_time (al salir). Respeta prefers-reduced-motion vía CSS (.reveal).
 */
export function useReveal<T extends HTMLElement>(sectionName?: string) {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let enteredAt = 0;
    let viewed = false;

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            el.classList.add('is-visible');
            if (sectionName && !viewed) {
              viewed = true;
              enteredAt = Date.now();
              track('section_viewed', { section: sectionName });
            }
          } else if (sectionName && enteredAt) {
            track('section_time', { section: sectionName, seconds: Math.round((Date.now() - enteredAt) / 1000) });
            enteredAt = 0;
          }
        }
      },
      { threshold: 0.2, rootMargin: '-40px' }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [sectionName]);

  return ref;
}

import { useReveal } from '@/hooks/useReveal';
import { cn } from '@/lib/utils';

export function Section({
  id, name, className, children,
}: { id?: string; name?: string; className?: string; children: React.ReactNode }) {
  const ref = useReveal<HTMLElement>(name);
  return (
    <section ref={ref} id={id} className={cn('reveal', className)}>
      {children}
    </section>
  );
}

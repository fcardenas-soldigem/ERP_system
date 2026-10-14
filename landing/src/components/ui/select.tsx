import * as React from 'react';
import { cn } from '@/lib/utils';

// Select nativo estilizado — liviano, accesible, sin dependencias de Radix.
const Select = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        'flex h-11 w-full rounded-md border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-ink-100 transition-[border-color,box-shadow] duration-[120ms] focus-visible:outline-none focus-visible:border-brand-400 focus-visible:ring-2 focus-visible:ring-brand-500/30 disabled:opacity-50',
        className
      )}
      {...props}
    >
      {children}
    </select>
  )
);
Select.displayName = 'Select';

export { Select };

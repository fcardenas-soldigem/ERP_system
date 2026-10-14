import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-[transform,background-color,box-shadow] duration-[120ms] ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98] [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-brand-500 text-white hover:bg-brand-400 shadow-[0_1px_0_0_rgba(255,255,255,0.08)_inset]',
        secondary: 'border border-ink-600 bg-ink-800 text-ink-100 hover:bg-ink-700 hover:border-ink-500',
        ghost: 'text-ink-200 hover:bg-ink-800',
      },
      size: {
        default: 'h-10 px-4 py-2',
        lg: 'h-12 px-6 text-base',
        sm: 'h-9 px-3',
      },
    },
    defaultVariants: { variant: 'primary', size: 'default' },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
  )
);
Button.displayName = 'Button';

export { Button, buttonVariants };

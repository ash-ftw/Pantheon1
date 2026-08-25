import { Loader2 } from 'lucide-react';
import React, { forwardRef } from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      iconLeft,
      iconRight,
      className = '',
      disabled,
      ...props
    },
    ref,
  ) => {
    // Base styles + variant mapping
    let variantClass = 'btn-primary';
    if (variant === 'secondary') variantClass = 'btn-secondary';
    if (variant === 'danger') variantClass = 'btn-danger';
    if (variant === 'outline') variantClass = 'btn-secondary';
    if (variant === 'ghost')
      variantClass =
        'bg-transparent hover:bg-[color-mix(in_srgb,var(--card-border)_50%,transparent)] text-foreground border-transparent';

    // Size adjustments
    let sizeStyle: React.CSSProperties = {};
    if (size === 'sm') {
      sizeStyle = { padding: '4px 12px', fontSize: '10px' };
    } else if (size === 'lg') {
      sizeStyle = { padding: '12px 24px', fontSize: '12px' };
    }

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${variantClass} ${className}`}
        style={{ ...sizeStyle, ...props.style }}
        {...props}
      >
        {isLoading ? <Loader2 className="animate-spin" size={size === 'sm' ? 12 : 14} /> : iconLeft}
        {children}
        {!isLoading && iconRight}
      </button>
    );
  },
);

Button.displayName = 'Button';

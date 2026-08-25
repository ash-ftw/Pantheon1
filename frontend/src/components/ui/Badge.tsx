import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?:
    'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info' | 'accent' | 'neutral';
  showDot?: boolean;
  pulseDot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'primary',
  showDot = false,
  pulseDot = false,
  className = '',
  ...props
}) => {
  const badgeClass =
    variant === 'neutral'
      ? 'bg-secondary text-secondary-foreground border border-card-border'
      : `badge badge-${variant}`;

  return (
    <span className={`${badgeClass} ${className}`} {...props}>
      {showDot && (
        <span
          className={`inline-block w-1.5 h-1.5 rounded-full mr-1 ${
            pulseDot ? 'animate-pulse' : ''
          }`}
          style={{ backgroundColor: 'currentColor' }}
        />
      )}
      {children}
    </span>
  );
};

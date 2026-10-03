import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  accentColor?: 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'accent' | 'none';
}

export const Card: React.FC<CardProps> = ({
  children,
  accentColor = 'none',
  className = '',
  style,
  ...props
}) => {
  let accentStyle: React.CSSProperties = {};
  if (accentColor !== 'none') {
    accentStyle = {
      borderTop: `2px solid var(--card-accent-${accentColor}, var(--${accentColor}))`,
    };
  }

  return (
    <div className={`card ${className}`} style={{ ...accentStyle, ...style }} {...props}>
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div className={`card-header flex items-center justify-between gap-4 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <h3 className={`card-title ${className}`} {...props}>
      {children}
    </h3>
  );
};

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <p
      className={`text-xs text-[var(--secondary-foreground)] mt-1.5 leading-relaxed ${className}`}
      {...props}
    >
      {children}
    </p>
  );
};

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div className={`card-body ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => {
  return (
    <div
      className={`px-5 py-3 border-t border-[var(--card-border)] bg-[rgba(0,0,0,0.2)] flex items-center justify-between ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

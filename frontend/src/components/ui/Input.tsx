import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, leftIcon, rightIcon, className = '', id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-mono font-medium text-[var(--secondary-foreground)] uppercase tracking-wider"
          >
            {label}
          </label>
        )}

        <div className="relative flex items-center">
          {leftIcon && (
            <div className="absolute left-3 text-[var(--muted-foreground)] pointer-events-none flex items-center">
              {leftIcon}
            </div>
          )}

          <input
            ref={ref}
            id={inputId}
            className={`input ${leftIcon ? 'pl-9' : ''} ${rightIcon ? 'pr-9' : ''} ${
              error ? 'border-[var(--danger)] focus:border-[var(--danger)]' : ''
            } ${className}`}
            {...props}
          />

          {rightIcon && (
            <div className="absolute right-3 text-[var(--muted-foreground)] pointer-events-none flex items-center">
              {rightIcon}
            </div>
          )}
        </div>

        {error && <span className="text-xs text-[var(--danger)] font-mono">{error}</span>}
        {!error && helperText && (
          <span className="text-xs text-[var(--muted-foreground)]">{helperText}</span>
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

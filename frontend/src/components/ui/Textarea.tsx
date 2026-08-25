import React, { forwardRef } from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, helperText, className = '', id, rows = 4, ...props }, ref) => {
    const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={textareaId}
            className="text-xs font-mono font-medium text-[var(--secondary-foreground)] uppercase tracking-wider"
          >
            {label}
          </label>
        )}

        <textarea
          ref={ref}
          id={textareaId}
          rows={rows}
          className={`input font-mono text-xs ${
            error ? 'border-[var(--danger)] focus:border-[var(--danger)]' : ''
          } ${className}`}
          {...props}
        />

        {error && <span className="text-xs text-[var(--danger)] font-mono">{error}</span>}
        {!error && helperText && (
          <span className="text-xs text-[var(--muted-foreground)]">{helperText}</span>
        )}
      </div>
    );
  },
);

Textarea.displayName = 'Textarea';

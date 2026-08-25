import React, { forwardRef } from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  helperText?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, error, helperText, className = '', id, ...props }, ref) => {
    const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="w-full flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={selectId}
            className="text-xs font-mono font-medium text-[var(--secondary-foreground)] uppercase tracking-wider"
          >
            {label}
          </label>
        )}

        <select
          ref={ref}
          id={selectId}
          className={`input cursor-pointer ${
            error ? 'border-[var(--danger)] focus:border-[var(--danger)]' : ''
          } ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option
              key={opt.value}
              value={opt.value}
              className="bg-[var(--secondary)] text-foreground"
            >
              {opt.label}
            </option>
          ))}
        </select>

        {error && <span className="text-xs text-[var(--danger)] font-mono">{error}</span>}
        {!error && helperText && (
          <span className="text-xs text-[var(--muted-foreground)]">{helperText}</span>
        )}
      </div>
    );
  },
);

Select.displayName = 'Select';

import { AlertCircle, AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import React from 'react';

export interface AlertProps {
  type?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
  children: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  children,
  onClose,
  className = '',
}) => {
  const getAlertConfig = () => {
    switch (type) {
      case 'success':
        return {
          bg: 'rgba(16, 185, 129, 0.08)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          color: 'var(--success)',
          icon: <CheckCircle2 size={16} />,
        };
      case 'warning':
        return {
          bg: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          color: 'var(--warning)',
          icon: <AlertTriangle size={16} />,
        };
      case 'danger':
        return {
          bg: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          color: 'var(--danger)',
          icon: <AlertCircle size={16} />,
        };
      case 'info':
      default:
        return {
          bg: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.25)',
          color: 'var(--info)',
          icon: <Info size={16} />,
        };
    }
  };

  const config = getAlertConfig();

  return (
    <div
      className={`p-4 rounded-[var(--radius)] flex gap-3 ${className}`}
      style={{ backgroundColor: config.bg, border: config.border }}
    >
      <div style={{ color: config.color }} className="shrink-0 mt-0.5">
        {config.icon}
      </div>
      <div className="flex-1">
        {title && (
          <h4
            className="font-mono text-xs font-semibold uppercase tracking-wider mb-1"
            style={{ color: config.color }}
          >
            {title}
          </h4>
        )}
        <div className="text-xs text-[var(--foreground)]">{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-[var(--secondary-foreground)] hover:text-foreground shrink-0 cursor-pointer"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
};

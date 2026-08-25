import { AlertCircle, AlertTriangle, CheckCircle2, Info, ShieldAlert } from 'lucide-react';
import React from 'react';

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info' | 'resolved' | 'active';

export interface SeverityBadgeProps {
  level: SeverityLevel;
  showIcon?: boolean;
  label?: string;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  level,
  showIcon = true,
  label,
  className = '',
}) => {
  const displayLabel = label || level.toUpperCase();

  const getSeverityConfig = () => {
    switch (level) {
      case 'critical':
        return {
          class: 'badge-danger',
          icon: <ShieldAlert size={12} />,
          textClass: 'severity-critical',
        };
      case 'high':
        return {
          class: 'badge-accent',
          icon: <AlertCircle size={12} />,
          textClass: 'severity-high',
        };
      case 'medium':
        return {
          class: 'badge-warning',
          icon: <AlertTriangle size={12} />,
          textClass: 'severity-medium',
        };
      case 'low':
      case 'info':
        return {
          class: 'badge-info',
          icon: <Info size={12} />,
          textClass: 'severity-low',
        };
      case 'resolved':
      case 'active':
        return {
          class: 'badge-success',
          icon: <CheckCircle2 size={12} />,
          textClass: 'severity-resolved',
        };
    }
  };

  const config = getSeverityConfig();

  return (
    <span className={`badge ${config.class} ${className}`}>
      {showIcon && config.icon}
      <span>{displayLabel}</span>
    </span>
  );
};

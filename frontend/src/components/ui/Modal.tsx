import { X } from 'lucide-react';
import React, { useEffect } from 'react';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'auto';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  let maxWidthClass = 'max-w-md';
  if (size === 'sm') maxWidthClass = 'max-w-sm';
  if (size === 'lg') maxWidthClass = 'max-w-2xl';
  if (size === 'xl') maxWidthClass = 'max-w-4xl';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-fade-in">
      <div
        className={`w-full ${maxWidthClass} bg-[var(--card)] border border-[var(--card-border)] rounded-[var(--radius)] shadow-2xl flex flex-col overflow-hidden animate-slide-in`}
      >
        <div className="px-5 py-4 border-b border-[var(--card-border)] flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm uppercase tracking-wider text-[var(--foreground)]">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="text-[var(--secondary-foreground)] hover:text-foreground cursor-pointer transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-5 overflow-y-auto max-h-[70vh] text-xs text-[var(--foreground)]">
          {children}
        </div>

        {footer && (
          <div className="px-5 py-3 border-t border-[var(--card-border)] bg-[rgba(0,0,0,0.2)] flex items-center justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

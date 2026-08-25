import { Check, Copy } from 'lucide-react';
import React, { useState } from 'react';

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  className?: string;
}

export const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language = 'bash',
  filename,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`rounded-[var(--radius)] border border-[var(--card-border)] bg-[#050709] overflow-hidden ${className}`}
    >
      {(filename || language) && (
        <div className="px-4 py-2 bg-[var(--secondary)] border-b border-[var(--card-border)] flex items-center justify-between font-mono text-[10px] text-[var(--secondary-foreground)]">
          <span>{filename || language.toUpperCase()}</span>
          <button
            onClick={copyToClipboard}
            className="flex items-center gap-1 hover:text-foreground cursor-pointer transition-colors"
          >
            {copied ? <Check size={12} className="text-[var(--success)]" /> : <Copy size={12} />}
            <span>{copied ? 'COPIED' : 'COPY'}</span>
          </button>
        </div>
      )}
      <pre className="p-4 font-mono text-xs text-[var(--foreground)] overflow-x-auto">
        <code>{code}</code>
      </pre>
    </div>
  );
};

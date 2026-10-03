import React from 'react';
import { Settings, Check, X, Sparkles, Moon } from 'lucide-react';
import { useThemeStore } from '../../stores/themeStore';

interface ThemeSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ThemeSettingsModal: React.FC<ThemeSettingsModalProps> = ({ isOpen, onClose }) => {
  const { theme, setTheme } = useThemeStore();

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="theme-settings-title"
      data-testid="theme-settings-modal"
    >
      <div
        className="w-full max-w-xl rounded border border-[var(--card-border)] bg-[var(--card)] shadow-2xl p-6 space-y-6 relative text-[var(--foreground)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--card-border)] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded bg-[var(--secondary)] border border-[var(--card-border)] text-[var(--foreground)]">
              <Settings size={18} />
            </div>
            <div>
              <h2
                id="theme-settings-title"
                className="font-display font-bold text-base tracking-wide uppercase"
              >
                Appearance & Theme Settings
              </h2>
              <p className="text-xs text-[var(--secondary-foreground)]">
                Select your preferred interface styling and palette
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors border border-transparent hover:border-[var(--card-border)]"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Theme Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 1. Cyber Obsidian */}
          <div
            onClick={() => setTheme('cyber-dark')}
            className={`p-4 rounded border cursor-pointer transition-all flex flex-col justify-between space-y-3 ${
              theme === 'cyber-dark'
                ? 'border-[#00d4aa] bg-[#07090d] ring-1 ring-[#00d4aa]/40'
                : 'border-[var(--card-border)] bg-[var(--secondary)] hover:border-[var(--secondary-foreground)]'
            }`}
            data-testid="select-cyber-theme-card"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 font-display font-bold text-sm tracking-wider">
                  <Sparkles size={14} className="text-[#00d4aa]" />
                  <span>CYBER OBSIDIAN</span>
                </div>
                {theme === 'cyber-dark' && (
                  <span className="flex items-center gap-1 font-mono text-[10px] text-[#00d4aa] bg-[#00d4aa]/10 px-2 py-0.5 rounded border border-[#00d4aa]/30">
                    <Check size={12} /> ACTIVE
                  </span>
                )}
              </div>
              <p className="text-[11px] text-[var(--secondary-foreground)] leading-relaxed">
                Default cyber aesthetic with neon cyan and orange accents on deep obsidian canvas.
              </p>
            </div>

            {/* Swatches */}
            <div className="pt-2 border-t border-white/5 space-y-1.5">
              <div className="text-[9px] font-mono text-[var(--muted-foreground)] uppercase">
                Palette Spec:
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#07090d]"
                  title="Canvas (#07090d)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#0d1117]"
                  title="Card (#0d1117)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#00d4aa]"
                  title="Cyan Accent (#00d4aa)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#ff6b35]"
                  title="Orange Accent (#ff6b35)"
                />
              </div>
            </div>
          </div>

          {/* 2. Matte Studio (Monochrome) */}
          <div
            onClick={() => setTheme('matte-mono')}
            className={`p-4 rounded border cursor-pointer transition-all flex flex-col justify-between space-y-3 ${
              theme === 'matte-mono'
                ? 'border-[#c8c8c8] bg-[#0f0f10] ring-1 ring-[#ffffff]/40'
                : 'border-[var(--card-border)] bg-[var(--secondary)] hover:border-[var(--secondary-foreground)]'
            }`}
            data-testid="select-matte-theme-card"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 font-display font-bold text-sm tracking-wider">
                  <Moon size={14} className="text-[#ffffff]" />
                  <span>MATTE STUDIO</span>
                </div>
                {theme === 'matte-mono' && (
                  <span className="flex items-center gap-1 font-mono text-[10px] text-[#ffffff] bg-white/10 px-2 py-0.5 rounded border border-white/30">
                    <Check size={12} /> ACTIVE
                  </span>
                )}
              </div>
              <p className="text-[11px] text-[var(--secondary-foreground)] leading-relaxed">
                Zero neon colors. Minimal monochrome palette with dark charcoal outlines and pure
                white accents.
              </p>
            </div>

            {/* Swatches */}
            <div className="pt-2 border-t border-white/5 space-y-1.5">
              <div className="text-[9px] font-mono text-[var(--muted-foreground)] uppercase">
                Palette Spec:
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#0f0f10]"
                  title="Matte Black (#0F0F10)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#232323]"
                  title="Charcoal (#232323)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#c8c8c8]"
                  title="Silver (#C8C8C8)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#eaeaea]"
                  title="Light Gray (#EAEAEA)"
                />
                <span
                  className="w-5 h-5 rounded border border-white/10 bg-[#ffffff]"
                  title="Pure White (#FFFFFF)"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Live Preview Bar */}
        <div className="p-3.5 rounded border border-[var(--card-border)] bg-[var(--secondary)] space-y-2">
          <div className="text-[10px] font-mono uppercase text-[var(--muted-foreground)] tracking-wider">
            Live Component Preview:
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className="btn-primary text-xs py-1.5 px-3">
              Primary Button
            </button>
            <button type="button" className="btn-secondary text-xs py-1.5 px-3">
              Secondary Button
            </button>
            <span className="badge badge-primary font-mono text-[10px]">Active Status</span>
            <span className="badge badge-accent font-mono text-[10px]">Highlight</span>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end pt-2 border-t border-[var(--card-border)]">
          <button type="button" onClick={onClose} className="btn-primary text-xs py-2 px-5">
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

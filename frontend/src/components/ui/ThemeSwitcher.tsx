import React, { useState } from 'react';
import { Settings } from 'lucide-react';
import { useThemeStore } from '../../stores/themeStore';
import { ThemeSettingsModal } from './ThemeSettingsModal';

interface ThemeSwitcherProps {
  className?: string;
  variant?: 'icon' | 'compact' | 'pill' | 'segmented';
  showLabel?: boolean;
}

export const ThemeSwitcher: React.FC<ThemeSwitcherProps> = ({
  className = '',
  showLabel = false,
}) => {
  const { theme } = useThemeStore();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setIsSettingsOpen(true)}
        className={`theme-settings-btn ${showLabel ? 'has-label' : ''} ${className}`}
        title="Theme & Appearance Settings"
        aria-label="Theme Settings"
        data-testid="theme-settings-open-btn"
      >
        <Settings size={18} className="theme-settings-icon" />
        {showLabel && (
          <span className="theme-settings-label font-mono text-xs">
            {theme === 'matte-mono' ? 'Matte Studio' : 'Cyber Obsidian'}
          </span>
        )}
      </button>

      <ThemeSettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </>
  );
};

export const ThemeSettingsButton = ThemeSwitcher;

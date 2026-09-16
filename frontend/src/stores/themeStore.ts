import { create } from 'zustand';

export type ThemeMode = 'cyber-dark' | 'matte-mono';

interface ThemeState {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
}

const STORAGE_KEY = 'pantheon-theme';

// Safe retrieval of initial theme
const getInitialTheme = (): ThemeMode => {
  if (typeof window === 'undefined') return 'matte-mono';
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'matte-mono' || saved === 'cyber-dark') {
      return saved;
    }
  } catch {
    // ignore storage access errors
  }
  return 'matte-mono';
};

const applyThemeToDOM = (theme: ThemeMode) => {
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.classList.remove('theme-cyber-dark', 'theme-matte-mono');
    document.documentElement.classList.add(`theme-${theme}`);
  }
};

export const useThemeStore = create<ThemeState>((set) => {
  const initialTheme = getInitialTheme();
  // Apply immediately on store initialization
  applyThemeToDOM(initialTheme);

  return {
    theme: initialTheme,
    setTheme: (theme: ThemeMode) => {
      try {
        localStorage.setItem(STORAGE_KEY, theme);
      } catch {
        // ignore
      }
      applyThemeToDOM(theme);
      set({ theme });
    },
    toggleTheme: () => {
      set((state) => {
        const nextTheme: ThemeMode = state.theme === 'cyber-dark' ? 'matte-mono' : 'cyber-dark';
        try {
          localStorage.setItem(STORAGE_KEY, nextTheme);
        } catch {
          // ignore
        }
        applyThemeToDOM(nextTheme);
        return { theme: nextTheme };
      });
    },
  };
});

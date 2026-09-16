import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { useThemeStore } from '../stores/themeStore';
import { ThemeSwitcher } from '../components/ui/ThemeSwitcher';

describe('Theme System & Palette Integration', () => {
  beforeEach(() => {
    localStorage.clear();
    act(() => {
      useThemeStore.getState().setTheme('matte-mono');
    });
  });

  it('initializes with matte-mono theme by default', () => {
    expect(useThemeStore.getState().theme).toBe('matte-mono');
    expect(document.documentElement.getAttribute('data-theme')).toBe('matte-mono');
  });

  it('switches to cyber-dark theme and updates document attributes', () => {
    act(() => {
      useThemeStore.getState().setTheme('cyber-dark');
    });

    expect(useThemeStore.getState().theme).toBe('cyber-dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('cyber-dark');
    expect(document.documentElement.classList.contains('theme-cyber-dark')).toBe(true);
    expect(localStorage.getItem('pantheon-theme')).toBe('cyber-dark');
  });

  it('toggles between matte-mono and cyber-dark correctly', () => {
    act(() => {
      useThemeStore.getState().toggleTheme();
    });
    expect(useThemeStore.getState().theme).toBe('cyber-dark');

    act(() => {
      useThemeStore.getState().toggleTheme();
    });
    expect(useThemeStore.getState().theme).toBe('matte-mono');
  });

  it('renders ThemeSwitcher as a standalone settings icon button matching notification bell', () => {
    render(<ThemeSwitcher />);

    const settingsBtn = screen.getByTestId('theme-settings-open-btn');
    expect(settingsBtn).toBeInTheDocument();
    expect(settingsBtn).toHaveClass('theme-settings-btn');
    expect(settingsBtn).toHaveAttribute('title', 'Theme & Appearance Settings');
    expect(settingsBtn).toHaveAttribute('aria-label', 'Theme Settings');

    // Does NOT render old segmented toggle buttons
    expect(screen.queryByTestId('theme-btn-cyber')).not.toBeInTheDocument();
    expect(screen.queryByTestId('theme-btn-matte')).not.toBeInTheDocument();
  });

  it('renders ThemeSwitcher with optional label when showLabel is true', () => {
    render(<ThemeSwitcher showLabel />);

    const settingsBtn = screen.getByTestId('theme-settings-open-btn');
    expect(settingsBtn).toBeInTheDocument();
    expect(settingsBtn).toHaveClass('has-label');
    expect(settingsBtn).toHaveTextContent('Matte Studio');
  });

  it('opens ThemeSettingsModal on clicking settings icon button and selects cyber theme', () => {
    render(<ThemeSwitcher />);

    const settingsBtn = screen.getByTestId('theme-settings-open-btn');
    expect(settingsBtn).toBeInTheDocument();

    act(() => {
      fireEvent.click(settingsBtn);
    });

    const modal = screen.getByTestId('theme-settings-modal');
    expect(modal).toBeInTheDocument();

    const cyberCard = screen.getByTestId('select-cyber-theme-card');
    act(() => {
      fireEvent.click(cyberCard);
    });

    expect(useThemeStore.getState().theme).toBe('cyber-dark');
    expect(document.documentElement.getAttribute('data-theme')).toBe('cyber-dark');
  });

  it('selects matte monochrome theme inside ThemeSettingsModal', () => {
    act(() => {
      useThemeStore.getState().setTheme('cyber-dark');
    });

    render(<ThemeSwitcher />);

    const settingsBtn = screen.getByTestId('theme-settings-open-btn');
    act(() => {
      fireEvent.click(settingsBtn);
    });

    const matteCard = screen.getByTestId('select-matte-theme-card');
    act(() => {
      fireEvent.click(matteCard);
    });

    expect(useThemeStore.getState().theme).toBe('matte-mono');
    expect(document.documentElement.getAttribute('data-theme')).toBe('matte-mono');
  });
});


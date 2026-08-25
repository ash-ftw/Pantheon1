/**
 * Vitest test setup — configures jest-dom matchers for React Testing Library.
 */
import '@testing-library/jest-dom';

// Ensure localStorage mock is present in test environment
if (typeof window !== 'undefined' && (!window.localStorage || typeof window.localStorage.getItem !== 'function')) {
  const store: Record<string, string> = {};
  const localStorageMock = {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      for (const k in store) {
        delete store[k];
      }
    },
    length: 0,
    key: (index: number) => Object.keys(store)[index] || null,
  };
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  });
}

import { create } from 'zustand';

export type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const getInitialTheme = (): Theme => {
  const saved = localStorage.getItem('rover_theme') as Theme;
  if (saved && ['light', 'dark', 'system'].includes(saved)) {
    return saved;
  }
  return 'dark';
};

const applyTheme = (theme: Theme) => {
  const root = document.documentElement;
  let isLight = false;
  if (theme === 'light') {
    isLight = true;
  } else if (theme === 'system') {
    isLight = window.matchMedia('(prefers-color-scheme: light)').matches;
  }

  if (isLight) {
    root.classList.add('light');
    root.classList.remove('dark');
  } else {
    root.classList.add('dark');
    root.classList.remove('light');
  }
};

export const useThemeStore = create<ThemeState>((set) => {
  const initialTheme = getInitialTheme();
  applyTheme(initialTheme);

  // Listen to system changes if theme is system
  if (typeof window !== 'undefined') {
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
      const currentTheme = localStorage.getItem('rover_theme') as Theme;
      if (currentTheme === 'system') {
        applyTheme('system');
      }
    });
  }

  return {
    theme: initialTheme,
    setTheme: (theme: Theme) => {
      localStorage.setItem('rover_theme', theme);
      applyTheme(theme);
      set({ theme });
    },
  };
});

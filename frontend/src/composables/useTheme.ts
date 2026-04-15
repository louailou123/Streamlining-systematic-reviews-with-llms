import { computed, ref, watch } from 'vue';

type ThemePreference = 'light' | 'dark';

const STORAGE_KEY = 'lira-theme-preference';
const preference = ref<ThemePreference | null>(null);
const systemPrefersDark = ref(false);
let initialized = false;
let watchInitialized = false;
let mediaQuery: MediaQueryList | null = null;

function applyTheme() {
  const resolved = preference.value ?? (systemPrefersDark.value ? 'dark' : 'light');
  document.documentElement.classList.toggle('app-dark', resolved === 'dark');
  document.documentElement.style.colorScheme = resolved;
}

function handleSystemChange(event: MediaQueryListEvent) {
  systemPrefersDark.value = event.matches;
  applyTheme();
}

export function useTheme() {
  if (!initialized && typeof window !== 'undefined') {
    initialized = true;
    mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    systemPrefersDark.value = mediaQuery.matches;

    const stored = window.localStorage.getItem(STORAGE_KEY);
    preference.value = stored === 'light' || stored === 'dark' ? stored : null;

    mediaQuery.addEventListener('change', handleSystemChange);
    applyTheme();
  }

  if (!watchInitialized) {
    watchInitialized = true;
    watch(preference, (value) => {
      if (typeof window !== 'undefined') {
        if (value) {
          window.localStorage.setItem(STORAGE_KEY, value);
        } else {
          window.localStorage.removeItem(STORAGE_KEY);
        }
      }

      applyTheme();
    });
  }

  const resolvedTheme = computed<ThemePreference>(() => {
    if (preference.value) {
      return preference.value;
    }

    return systemPrefersDark.value ? 'dark' : 'light';
  });

  function toggleTheme() {
    preference.value = resolvedTheme.value === 'dark' ? 'light' : 'dark';
  }

  return {
    preference,
    resolvedTheme,
    toggleTheme,
  };
}

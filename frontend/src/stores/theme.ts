import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { theme } from 'ant-design-vue'

type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'fitness-theme-mode'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>('light')

  const isDark = computed(() => mode.value === 'dark')

  const antTheme = computed(() => ({
    algorithm: isDark.value ? theme.darkAlgorithm : theme.defaultAlgorithm,
  }))

  function applyMode(val: ThemeMode) {
    mode.value = val
    if (val === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem(STORAGE_KEY, val)
  }

  function toggleTheme() {
    applyMode(isDark.value ? 'light' : 'dark')
  }

  function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
    if (saved) {
      applyMode(saved)
    } else {
      // 首次访问：跟随系统偏好
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      applyMode(prefersDark ? 'dark' : 'light')
    }
  }

  return { mode, isDark, antTheme, toggleTheme, initTheme }
})

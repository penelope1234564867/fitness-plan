<template>
  <div id="app">
    <!-- 全屏模式（向导页/生成页） -->
    <router-view v-if="!showLayout" />

    <!-- 已 onboarding：固定 header + 内容切换 -->
    <template v-else>
      <header class="main-header">
        <div class="header-inner">
          <div class="header-left" @click="goHome">
            <span class="header-logo">💪</span>
            <h1 class="header-title">AI 智能健身助手</h1>
          </div>
          <div class="header-right">
            <div class="avatar-btn" @click="goProfile">
              <span class="avatar-icon">{{ avatarLabel }}</span>
            </div>
          </div>
        </div>
      </header>
      <div class="main-body">
        <router-view />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const layoutRoutes = ['/home', '/profile']
const showLayout = computed(() => layoutRoutes.includes(route.path))

const avatarLabel = computed(() => {
  const p = userStore.profile
  if (p?.gender === 'male') return '♂'
  if (p?.gender === 'female') return '♀'
  return '👤'
})

function goHome() {
  router.push('/home')
}
function goProfile() {
  router.push('/profile')
}
</script>

<style>
html, body { margin: 0; padding: 0; height: 100%; }
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

/* ── 固定 header ── */
.main-header {
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1440px;
  margin: 0 auto;
  padding: 12px 24px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.header-logo { font-size: 24px; }
.header-title { font-size: 18px; font-weight: 700; color: #1a1a1a; margin: 0; }
.header-right { display: flex; align-items: center; gap: 12px; }
.avatar-btn {
  width: 36px; height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #fb923c);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: transform 0.2s;
  font-size: 16px;
}
.avatar-btn:hover { transform: scale(1.1); }
.avatar-icon { color: #fff; font-weight: 700; }

/* ── 主内容区（路由切换） ── */
.main-body {
  flex: 1;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 16px 24px;
  min-height: 0;
  box-sizing: border-box;
}
</style>

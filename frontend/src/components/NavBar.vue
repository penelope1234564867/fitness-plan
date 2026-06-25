<template>
  <a-layout-header
    style="
      background: #fff;
      padding: 0 24px;
      display: flex;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    "
  >
    <div style="font-size: 20px; font-weight: 700; margin-right: 40px; white-space: nowrap; color: #00b09b;">
      💪 智能健身助手
    </div>
    <div style="flex: 1; display: flex; align-items: center;">
      <a-menu
        v-model:selectedKeys="currentRoute"
        mode="horizontal"
        style="flex: 1; border-bottom: none;"
        @click="handleMenuClick"
      >
        <a-menu-item key="/calendar">
          <template #icon>📅</template>
          训练计划
        </a-menu-item>
      </a-menu>
      <a-menu
        v-model:selectedKeys="currentRoute"
        mode="horizontal"
        style="border-bottom: none; margin-left: auto;"
        @click="handleMenuClick"
      >
        <a-menu-item key="/profile">
          <template #icon>👤</template>
          个人主页
        </a-menu-item>
      </a-menu>
    </div>
  </a-layout-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed<string[]>(() => {
  const path = route.path
  if (path.startsWith('/calendar') || path === '/') return ['/calendar']
  if (path.startsWith('/profile')) return ['/profile']
  return ['/calendar']
})

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
}
</script>

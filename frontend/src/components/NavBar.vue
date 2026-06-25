<template>
  <a-layout-header style="background: #001529; padding: 0 24px; display: flex; align-items: center; position: sticky; top: 0; z-index: 100;">
    <div style="color: white; font-size: 20px; font-weight: bold; margin-right: 40px; white-space: nowrap;">
      💪 智能健身助手
    </div>
    <a-menu
      v-model:selectedKeys="currentRoute"
      mode="horizontal"
      theme="dark"
      style="flex: 1; min-width: 0;"
      @click="handleMenuClick"
    >
      <a-menu-item key="/">
        <template #icon>🏠</template>
        首页
      </a-menu-item>
      <a-menu-item key="/plan">
        <template #icon>📋</template>
        训练计划
      </a-menu-item>
      <a-menu-item key="/record">
        <template #icon>📝</template>
        训练记录
      </a-menu-item>
      <a-menu-item key="/progress">
        <template #icon>📊</template>
        进度追踪
      </a-menu-item>
    </a-menu>
  </a-layout-header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const currentRoute = computed<string[]>(() => {
  const path = route.path
  if (path === '/') return ['/']
  if (path.startsWith('/plan')) return ['/plan']
  if (path.startsWith('/record')) return ['/record']
  if (path.startsWith('/progress')) return ['/progress']
  return ['/']
})

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
}
</script>

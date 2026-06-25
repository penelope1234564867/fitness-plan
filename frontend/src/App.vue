<template>
  <div id="app">
    <a-layout style="min-height: 100vh">
      <NavBar v-if="showNav" />
      <a-layout-content :style="contentStyle">
        <router-view />
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()
const showNav = computed(() => route.path !== '/')
const contentStyle = computed(() => ({
  padding: showNav.value ? '24px' : '0',
  background: showNav.value ? '#f5f7fa' : 'transparent',
  minHeight: showNav.value ? 'auto' : 'calc(100vh - 64px)',
}))
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>

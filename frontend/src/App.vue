<template>
  <div id="app">
    <a-layout style="min-height: 100vh">
      <NavBar />
      <a-layout-content style="padding: 24px; background: #f5f7fa;">
        <router-view />
      </a-layout-content>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import NavBar from './components/NavBar.vue'
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    'Noto Sans', sans-serif;
}
</style>

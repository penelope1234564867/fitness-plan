import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'

import OnboardingGuide from './views/OnboardingGuide.vue'
import MainPage from './views/MainPage.vue'
import ProfilePage from './views/ProfilePage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Onboarding', component: OnboardingGuide },
    { path: '/home', name: 'Home', component: MainPage },
    { path: '/profile', name: 'Profile', component: ProfilePage },
    // 旧路由重定向
    { path: '/calendar', redirect: '/home' },
    { path: '/checklist', redirect: '/home' },
  ],
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

app.mount('#app')

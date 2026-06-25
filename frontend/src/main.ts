import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'

import OnboardingGuide from './views/OnboardingGuide.vue'
import CalendarView from './views/CalendarView.vue'
import WorkoutChecklist from './views/WorkoutChecklist.vue'
import ProfilePage from './views/ProfilePage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Onboarding', component: OnboardingGuide },
    { path: '/calendar', name: 'Calendar', component: CalendarView },
    { path: '/checklist', name: 'WorkoutChecklist', component: WorkoutChecklist },
    { path: '/profile', name: 'Profile', component: ProfilePage },
  ],
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

app.mount('#app')

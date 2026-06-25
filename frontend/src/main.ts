import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import App from './App.vue'

import Home from './views/Home.vue'
import Plan from './views/Plan.vue'
import Record from './views/Record.vue'
import Progress from './views/Progress.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: Home },
    { path: '/plan', name: 'Plan', component: Plan },
    { path: '/plan/:id', name: 'PlanDetail', component: Plan },
    { path: '/record', name: 'Record', component: Record },
    { path: '/progress', name: 'Progress', component: Progress },
  ],
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

app.mount('#app')

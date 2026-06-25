<template>
  <div class="plan-container">
    <!-- 计划概览头部 -->
    <div v-if="currentPlan" class="plan-header">
      <a-page-header
        :title="planTitle"
        :sub-title="`计划时长: ${currentPlan.duration_weeks} 周 · 每周 ${currentPlan.days_per_week} 天`"
        @back="goToPlanList"
      >
        <template #extra>
          <a-space>
            <a-tag color="green">{{ currentPlan.goal }}</a-tag>
            <a-tag color="blue">{{ currentPlan.experience_level }}</a-tag>
            <a-tag color="orange">{{ currentPlan.workout_location }}</a-tag>
          </a-space>
        </template>
      </a-page-header>
    </div>

    <!-- 计划列表视图 -->
    <div v-if="!planId && !currentPlan">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <a-spin size="large" />
        <p>加载中...</p>
      </div>

      <!-- 空状态 -->
      <div v-else-if="planList.length === 0" class="empty-state">
        <div class="empty-icon">🏋️</div>
        <h3>还没有训练计划</h3>
        <p>先去首页填写健身目标，AI 将为你生成专属计划</p>
        <a-button type="primary" size="large" @click="goHome" class="cta-button">
          🚀 开始创建
        </a-button>
      </div>

      <!-- 计划列表 -->
      <div v-else class="plan-list">
        <h2 class="section-title">📋 我的训练计划</h2>
        <a-row :gutter="[16, 16]">
          <a-col
            v-for="plan in planList"
            :key="plan.id"
            :xs="24"
            :sm="12"
            :md="8"
          >
            <a-card
              hoverable
              class="plan-summary-card"
              @click="viewPlan(plan.id)"
            >
              <template #cover>
                <div class="card-cover">
                  <span class="cover-icon">{{ goalIcons[plan.goal] || '💪' }}</span>
                </div>
              </template>
              <a-card-meta>
                <template #title>
                  <span>{{ goalIcons[plan.goal] || '💪' }} {{ plan.goal }}计划</span>
                </template>
                <template #description>
                  <div class="plan-meta">
                    <p>📅 {{ plan.duration_weeks }} 周 · 每周 {{ plan.days_per_week }} 天</p>
                    <p class="plan-date">创建于 {{ formatDate(plan.created_at) }}</p>
                  </div>
                </template>
              </a-card-meta>
            </a-card>
          </a-col>
        </a-row>
      </div>
    </div>

    <!-- 计划详情视图 -->
    <div v-else-if="currentPlan" class="plan-detail">
      <!-- 周 Tab -->
      <a-tabs v-model:activeKey="activeWeek" tab-position="top" type="card" class="week-tabs">
        <a-tab-pane
          v-for="week in currentPlan.weekly_plans"
          :key="String(week.week)"
          :tab="`第 ${week.week} 周`"
        >
          <div class="week-content">
            <a-row :gutter="16">
              <a-col :span="18">
                <PlanCard
                  v-for="(day, i) in week.days"
                  :key="i"
                  :workout="day"
                />
              </a-col>
              <a-col :span="6">
                <DietTips :diet="currentPlan.diet" />
                <!-- 跳转到记录页 -->
                <a-card class="quick-actions" :bordered="false" style="margin-top: 16px">
                  <a-button type="primary" block @click="goToRecord">
                    📝 记录训练
                  </a-button>
                </a-card>
              </a-col>
            </a-row>
          </div>
        </a-tab-pane>
      </a-tabs>

      <!-- 没有 weekly_plans 时的提示 -->
      <div v-if="!currentPlan.weekly_plans?.length" class="empty-section">
        <a-empty description="计划详情加载中...">
          <a-button type="primary" @click="refreshPlan">
            重新加载
          </a-button>
        </a-empty>
      </div>
    </div>

    <!-- 加载状态（详情模式） -->
    <div v-if="loading && planId" class="loading-state">
      <a-spin size="large" />
      <p>加载计划详情...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlanStore } from '@/stores/plan'
import PlanCard from '@/components/PlanCard.vue'
import DietTips from '@/components/DietTips.vue'

const route = useRoute()
const router = useRouter()
const planStore = usePlanStore()

const activeWeek = ref('1')
const planId = computed(() => {
  const id = route.params.id
  return id ? Number(id) : null
})

const currentPlan = computed(() => planStore.currentPlan)
const planList = computed(() => planStore.planList)
const loading = computed(() => planStore.loading)

const planTitle = computed(() => {
  if (!currentPlan.value) return ''
  const icons: Record<string, string> = { '减脂': '🔥', '增肌': '💪', '塑形': '✨', '保持健康': '🌿' }
  return `${icons[currentPlan.value.goal] || ''} ${currentPlan.value.goal}训练计划`
})

const goalIcons: Record<string, string> = {
  '减脂': '🔥',
  '增肌': '💪',
  '塑形': '✨',
  '保持健康': '🌿',
}

onMounted(async () => {
  if (planId.value) {
    await planStore.fetchPlan(planId.value)
  } else {
    await planStore.fetchPlans()
    // 如果是从首页生成后跳转来的，自动进入最新计划
    if (currentPlan.value && !route.params.id) {
      // 已通过 createPlan 设置了 currentPlan
    }
  }
})

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return dateStr.slice(0, 10)
}

function viewPlan(id: number) {
  router.push(`/plan/${id}`)
}

function goToPlanList() {
  planStore.clearCurrent()
  router.push('/plan')
}

function goHome() {
  router.push('/')
}

function goToRecord() {
  if (currentPlan.value) {
    router.push(`/record?plan_id=${currentPlan.value.id}`)
  } else {
    router.push('/record')
  }
}

function refreshPlan() {
  if (planId.value) {
    planStore.fetchPlan(planId.value)
  }
}
</script>

<style scoped>
.plan-container {
  max-width: 1200px;
  margin: 0 auto;
}
.plan-header {
  margin-bottom: 20px;
  background: white;
  border-radius: 12px;
  padding: 8px 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.section-title {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}
.plan-list {
  animation: fadeInUp 0.5s ease-out;
}

/* 计划概要卡片 */
.plan-summary-card {
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}
.plan-summary-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.card-cover {
  height: 120px;
  background: linear-gradient(135deg, #00b09b, #96c93d);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cover-icon {
  font-size: 48px;
}
.plan-meta p {
  margin: 4px 0;
  font-size: 13px;
  color: #666;
}
.plan-date {
  font-size: 12px;
  color: #999;
}

/* 周 Tab */
.week-content {
  min-height: 400px;
}

/* 空状态 & 加载 */
.loading-state, .empty-state {
  text-align: center;
  padding: 80px 20px;
  animation: fadeInUp 0.5s ease-out;
}
.empty-icon {
  font-size: 80px;
  margin-bottom: 16px;
}
.empty-state h3 {
  font-size: 22px;
  color: #333;
  margin-bottom: 8px;
}
.empty-state p {
  color: #999;
  margin-bottom: 24px;
}
.cta-button {
  height: 48px;
  border-radius: 24px;
  font-size: 16px;
}
.empty-section {
  padding: 60px 20px;
  text-align: center;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

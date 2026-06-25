<template>
  <div class="profile-container">
    <div class="profile-card">
      <div class="profile-avatar">
        <span class="avatar-icon">{{ userStore.profile?.gender === 'male' ? '♂' : '♀' }}</span>
      </div>
      <h2 class="profile-name">
        {{ userStore.profile?.height || '?' }}cm · {{ userStore.profile?.weight || '?' }}kg
      </h2>
      <p class="profile-goal">{{ userStore.profile?.goal || '未设置' }}</p>

      <a-divider />

      <!-- 信息列表 -->
      <div v-if="!editing" class="info-list">
        <div class="info-row">
          <span class="info-label">身高</span>
          <span class="info-value">{{ profileData.height || '-' }} cm</span>
        </div>
        <div class="info-row">
          <span class="info-label">体重</span>
          <span class="info-value">{{ profileData.weight || '-' }} kg</span>
        </div>
        <div class="info-row">
          <span class="info-label">年龄</span>
          <span class="info-value">{{ profileData.age || '-' }} 岁</span>
        </div>
        <div class="info-row">
          <span class="info-label">性别</span>
          <span class="info-value">{{ profileData.gender === 'male' ? '男' : profileData.gender === 'female' ? '女' : '-' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">目标</span>
          <span class="info-value">{{ profileData.goal || '-' }}</span>
        </div>
      </div>

      <!-- 编辑模式 -->
      <a-form v-else layout="vertical" class="edit-form">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="身高 (cm)">
              <a-input-number v-model:value="editData.height" :min="100" :max="250" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="体重 (kg)">
              <a-input-number v-model:value="editData.weight" :min="30" :max="250" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="年龄">
              <a-input-number v-model:value="editData.age" :min="10" :max="100" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="性别">
              <a-select v-model:value="editData.gender" style="width: 100%">
                <a-select-option value="male">男</a-select-option>
                <a-select-option value="female">女</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="目标">
          <a-select v-model:value="editData.goal" style="width: 100%">
            <a-select-option value="减脂">🔥 减脂</a-select-option>
            <a-select-option value="增肌">💪 增肌</a-select-option>
            <a-select-option value="塑形">✨ 塑形</a-select-option>
            <a-select-option value="保持健康">🌿 保持健康</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>

      <div class="profile-actions">
        <a-button v-if="!editing" type="primary" block size="large" @click="startEdit">
          ✏️ 编辑资料
        </a-button>
        <template v-else>
          <a-button type="primary" block size="large" :loading="saving" @click="saveEdit">
            💾 保存
          </a-button>
          <a-button block size="large" style="margin-top: 8px;" @click="cancelEdit">
            取消
          </a-button>
        </template>
      </div>

      <a-divider />

      <a-button block size="large" class="regenerate-btn" :loading="regenerating" @click="onRegenerate">
        🔄 重新生成计划
      </a-button>

      <!-- 统计数据 -->
      <div v-if="hasStats" class="stats-section">
        <a-divider />
        <h3 class="stats-title">📊 训练统计</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-value">{{ userStore.stats.totalWorkoutDays }}</span>
            <span class="stat-label">总训练天数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ userStore.stats.currentStreak }}</span>
            <span class="stat-label">连续天数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ userStore.stats.monthlyDone }}/{{ userStore.stats.monthlyTotal }}</span>
            <span class="stat-label">本月完成</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useWorkoutStore } from '@/stores/workout'

const router = useRouter()
const userStore = useUserStore()
const workoutStore = useWorkoutStore()

const editing = ref(false)
const saving = ref(false)
const regenerating = ref(false)

const profileData = computed(() => ({
  height: userStore.profile?.height,
  weight: userStore.profile?.weight,
  age: userStore.profile?.age,
  gender: userStore.profile?.gender,
  goal: userStore.profile?.goal,
}))

const hasStats = computed(() => userStore.stats.totalWorkoutDays > 0)

const editData = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
  goal: undefined as string | undefined,
})

onMounted(() => {
  userStore.fetchProfile().catch(() => {})
  loadEditData()
})

function loadEditData() {
  editData.height = userStore.profile?.height
  editData.weight = userStore.profile?.weight
  editData.age = userStore.profile?.age
  editData.gender = userStore.profile?.gender
  editData.goal = userStore.profile?.goal
}

function startEdit() {
  loadEditData()
  editing.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    await userStore.saveProfile({
      height: editData.height,
      weight: editData.weight,
      age: editData.age,
      gender: editData.gender,
      goal: editData.goal,
    })
    message.success('资料已更新')
    editing.value = false
  } catch (e: any) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  editing.value = false
}

function onRegenerate() {
  Modal.confirm({
    title: '重新生成计划',
    content: '将根据你最新的资料重新生成训练计划，确认吗？',
    okText: '确认生成',
    cancelText: '取消',
    onOk: async () => {
      regenerating.value = true
      try {
        const goal = userStore.profile?.goal || '保持健康'
        const location = userStore.profile?.gender === 'female' ? '居家' : '健身房'
        await workoutStore.createPlan({
          goal,
          experience_level: '新手',
          workout_location: location,
          days_per_week: 3,
          duration_weeks: 4,
          diet_preference: '普通',
        })
        message.success('新计划已生成！')
        setTimeout(() => router.push('/calendar'), 500)
      } catch (e: any) {
        message.error(e.message || '生成失败')
      } finally {
        regenerating.value = false
      }
    },
  })
}
</script>

<style scoped>
.profile-container { max-width: 520px; margin: 0 auto; }
.profile-card {
  background: #fff; border-radius: 20px; padding: 32px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.profile-avatar { text-align: center; margin-bottom: 12px; }
.avatar-icon {
  display: inline-flex; width: 64px; height: 64px; border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff; font-size: 28px; align-items: center; justify-content: center;
}
.profile-name { text-align: center; font-size: 22px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.profile-goal { text-align: center; font-size: 14px; color: #f97316; font-weight: 500; margin: 0; }

.info-list { display: flex; flex-direction: column; gap: 12px; }
.info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.info-row:last-child { border-bottom: none; }
.info-label { font-size: 14px; color: #888; }
.info-value { font-size: 14px; font-weight: 600; color: #333; }

.edit-form { margin: 16px 0; }

.profile-actions { margin-top: 20px; }
.profile-actions .ant-btn-primary { background: linear-gradient(135deg, #f97316, #fb923c); border: none; box-shadow: 0 4px 14px rgba(249,115,22,0.3); }

.regenerate-btn { border-color: #22c55e; color: #22c55e; font-weight: 600; height: 48px; border-radius: 12px; }
.regenerate-btn:hover { background: #f0fdf4; border-color: #22c55e; color: #22c55e; }

.stats-section { margin-top: 8px; }
.stats-title { font-size: 16px; font-weight: 600; color: #333; margin: 0 0 16px 0; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-item { text-align: center; padding: 16px; background: #f9fafb; border-radius: 12px; }
.stat-value { font-size: 20px; font-weight: 700; color: #f97316; display: block; }
.stat-label { font-size: 12px; color: #999; margin-top: 4px; display: block; }
</style>

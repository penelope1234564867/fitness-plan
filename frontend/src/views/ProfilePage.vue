<template>
  <div class="profile-page">
    <!-- ═══ 左侧 ═══ -->
    <div class="profile-left">

      <!-- 头像 + 名字行 -->
      <div class="avatar-section">
        <div class="avatar-icon">{{ userStore.profile?.gender === 'male' ? '♂' : '♀' }}</div>
        <h2 class="profile-name">{{ displayName }}</h2>
        <p class="profile-goal">{{ userStore.profile?.goal || '未设置目标' }}</p>
      </div>

      <!-- 个人信息 -->
      <div class="card">
        <div class="card-header"><span>✏️</span> 个人信息</div>
        <div class="info-grid">
          <div class="field">
            <label>身高 (cm)</label>
            <input v-model.number="form.height" type="number" placeholder="180" />
          </div>
          <div class="field">
            <label>体重 (kg)</label>
            <input v-model.number="form.weight" type="number" placeholder="72" />
          </div>
          <div class="field">
            <label>年龄</label>
            <input v-model.number="form.age" type="number" placeholder="28" />
          </div>
          <div class="field">
            <label>性别</label>
            <div class="btn-pair">
              <button class="opt-btn" :class="{ active: form.gender === 'male' }"
                @click="form.gender = 'male'">♂ 男</button>
              <button class="opt-btn" :class="{ active: form.gender === 'female' }"
                @click="form.gender = 'female'">♀ 女</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 健身目标 -->
      <div class="card">
        <div class="card-header"><span>🎯</span> 健身目标</div>
        <div class="goal-grid">
          <button v-for="g in goalOptions" :key="g.value"
            class="opt-btn goal-btn"
            :class="{ active: form.goal === g.value }"
            @click="form.goal = g.value">{{ g.label }}</button>
        </div>
      </div>

      <!-- 训练状态 -->
      <div class="card">
        <div class="card-header"><span>⚙️</span> 训练状态</div>

        <div class="state-row">
          <label>经验</label>
          <div class="btn-triple">
            <button v-for="e in expOptions" :key="e.value"
              class="opt-btn"
              :class="{ active: form.experience_level === e.value }"
              @click="form.experience_level = e.value">{{ e.label }}</button>
          </div>
        </div>

        <div class="state-row">
          <label>地点</label>
          <div class="btn-triple">
            <button v-for="l in locOptions" :key="l.value"
              class="opt-btn"
              :class="{ active: form.workout_location === l.value }"
              @click="form.workout_location = l.value">{{ l.label }}</button>
          </div>
        </div>

        <div class="state-row">
          <label>训练日</label>
          <div class="day-picker">
            <span v-for="d in dayOptions" :key="d.value"
              class="day-chip"
              :class="{ active: selectedDays.includes(d.value) }"
              @click="toggleDay(d.value)">{{ d.label }}</span>
          </div>
        </div>
        <p class="day-count">每周 {{ selectedDays.length }} 天</p>
      </div>

      <!-- 保存按钮 -->
      <button class="save-all-btn" :disabled="saving" @click="handleSave">
        {{ saving ? '⏳ 保存中...' : '💾 保存全部设置' }}
      </button>
    </div>

    <!-- ═══ 右侧 ═══ -->
    <div class="profile-right">
      <CycleRoadmapNew
        v-if="cycleStore.roadmapData"
        :data="cycleStore.roadmapData"
        :goal="cycleStore.macrocycle?.goal || '增肌'"
        :completed-days="completedDays"
        :total-days="totalDays"
        :next-phase-label="cycleStore.nextPhaseLabel ?? undefined"
      />
      <div v-else class="empty-state">
        <p>暂无训练计划</p>
        <p class="empty-sub">完成引导设置后，这里将显示您的训练周期路线图</p>
      </div>

      <TrainingKnowledgeCard />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useCycleStore } from '@/stores/cycle'
import { saveProfileCombined } from '@/services/api'
import CycleRoadmapNew from '@/components/CycleRoadmapNew.vue'
import TrainingKnowledgeCard from '@/components/TrainingKnowledgeCard.vue'

const router = useRouter()
const userStore = useUserStore()
const cycleStore = useCycleStore()

const saving = ref(false)

const goalOptions = [
  { value: '增肌', label: '💪 增肌' },
  { value: '减脂', label: '🔥 减脂' },
  { value: '塑形', label: '✨ 塑形' },
  { value: '保持健康', label: '❤️ 保持健康' },
]
const expOptions = [
  { value: '新手', label: '🌱 新手' },
  { value: '中级', label: '💪 中级' },
  { value: '高级', label: '🔥 高级' },
]
const locOptions = [
  { value: '居家', label: '🏠 居家' },
  { value: '健身房', label: '🏋️ 健身房' },
  { value: '户外', label: '🌳 户外' },
]
const dayOptions = [
  { value: 1, label: '一' }, { value: 2, label: '二' }, { value: 3, label: '三' },
  { value: 4, label: '四' }, { value: 5, label: '五' }, { value: 6, label: '六' }, { value: 7, label: '日' },
]

const form = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
  goal: undefined as string | undefined,
  experience_level: '新手',
  workout_location: '居家',
  preferredDays: '1,3,5',
})

const selectedDays = computed(() =>
  form.preferredDays.split(',').map(Number).filter(Boolean)
)

const displayName = computed(() => {
  const p = userStore.profile
  if (!p) return '设置你的个人信息'
  return `${p.gender === 'male' ? '♂' : '♀'} ${p.height || '?'}cm · ${p.weight || '?'}kg`
})

const completedDays = computed(() =>
  cycleStore.currentWeek?.days.filter((d: any) => d.is_completed).length ?? 0
)
const totalDays = computed(() =>
  cycleStore.currentWeek?.days.length ?? 0
)

function toggleDay(value: number) {
  const arr = selectedDays.value.slice()
  const idx = arr.indexOf(value)
  if (idx >= 0) arr.splice(idx, 1)
  else { arr.push(value); arr.sort() }
  form.preferredDays = arr.join(',')
}

async function handleSave() {
  saving.value = true
  try {
    await saveProfileCombined({
      height: form.height ?? null,
      weight: form.weight ?? null,
      age: form.age ?? null,
      gender: form.gender ?? null,
      goal: form.goal ?? null,
      experience_level: form.experience_level,
      workout_location: form.workout_location,
      preferred_days: form.preferredDays,
    })
    await userStore.fetchProfile()
    await userStore.fetchCurrentState()
  } catch (e: any) {
    console.error('保存失败:', e)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await userStore.fetchProfile().catch(() => {})
  await userStore.fetchCurrentState()
  cycleStore.fetchMacrocycles().catch(() => {})

  if (userStore.profile) {
    form.height = userStore.profile.height ?? undefined
    form.weight = userStore.profile.weight ?? undefined
    form.age = userStore.profile.age ?? undefined
    form.gender = userStore.profile.gender ?? undefined
    form.goal = userStore.profile.goal ?? undefined
  }
  if (userStore.currentState) {
    form.experience_level = userStore.currentState.experience_level || '新手'
    form.workout_location = userStore.currentState.workout_location || '居家'
    form.preferredDays = userStore.currentState.preferred_days || '1,3,5'
  }
})
</script>

<style scoped>
.profile-page {
  display: flex;
  gap: 24px;
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
  align-items: stretch;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── 左侧 ── */
.profile-left {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.avatar-section {
  background: #fff;
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
  text-align: center;
}

.avatar-icon {
  display: inline-flex;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  font-size: 26px;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.profile-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 4px;
}

.profile-goal {
  font-size: 13px;
  color: #f97316;
  font-weight: 500;
  margin: 0;
}

/* ── 卡片 ── */
.card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 14px;
}

/* ── 个人信息 2×2 ── */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.field label {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
  display: block;
}

.field input {
  width: 100%;
  border: 1.5px solid #eee;
  background: #f8f8f8;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
  outline: none;
  font-family: inherit;
  box-sizing: border-box;
}

.field input:focus {
  border-color: #f97316;
}

/* ── 按钮通用 ── */
.opt-btn {
  padding: 7px 0;
  border-radius: 8px;
  border: 1.5px solid #eee;
  background: #f8f8f8;
  color: #999;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
  font-family: inherit;
  box-sizing: border-box;
  line-height: 1;
}

.opt-btn.active {
  background: #fff7ed;
  border-color: #f97316;
  color: #f97316;
  font-weight: 700;
}

.opt-btn:hover:not(.active) {
  border-color: #ddd;
}

.btn-pair {
  display: flex;
  gap: 6px;
}
.btn-pair .opt-btn {
  flex: 1;
}

/* ── 健身目标 2×2 ── */
.goal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.goal-btn {
  padding: 10px 0;
  font-size: 14px;
}

/* ── 训练状态 ── */
.state-row {
  margin-bottom: 12px;
}
.state-row:last-child {
  margin-bottom: 0;
}
.state-row > label {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
  display: block;
}

.btn-triple {
  display: flex;
  gap: 6px;
}
.btn-triple .opt-btn {
  flex: 1;
}

.day-picker {
  display: flex;
  gap: 6px;
}

.day-chip {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  border: 1.5px solid #eee;
  background: #fff;
  color: #999;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}

.day-chip:hover {
  border-color: #f97316;
}

.day-chip.active {
  background: #f97316;
  border-color: #f97316;
  color: #fff;
}

.day-count {
  font-size: 12px;
  color: #888;
  margin: 8px 0 0;
}

/* ── 保存按钮 ── */
.save-all-btn {
  width: 100%;
  padding: 13px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-sizing: border-box;
  transition: box-shadow 0.2s;
  font-family: inherit;
}

.save-all-btn:hover:not(:disabled) {
  box-shadow: 0 4px 14px rgba(249,115,22,0.3);
}

.save-all-btn:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

/* ── 右侧 ── */
.profile-right {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.empty-state {
  background: #fff;
  border-radius: 14px;
  padding: 40px;
  text-align: center;
  border: 1px solid #f0f0f0;
}

.empty-state p {
  font-size: 15px;
  color: #888;
  margin: 0 0 8px;
}

.empty-sub {
  font-size: 13px;
  color: #bbb;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .profile-page {
    flex-direction: column;
  }
  .profile-left {
    width: 100%;
  }
}
</style>

<template>
  <div class="profile-page">
    <!-- ═══ 左侧 ═══ -->
    <div class="profile-left">

      <!-- 头像 + 名字行（紧凑） -->
      <div class="avatar-section">
        <div class="avatar-icon">{{ userStore.profile?.gender === 'male' ? '♂' : '♀' }}</div>
        <div class="avatar-info">
          <h2 class="profile-name">{{ displayName }}</h2>
          <p class="profile-goal">{{ userStore.profile?.goal || '未设置目标' }}</p>
        </div>
      </div>

      <!-- 中间卡片区 -->
      <div class="cards-area">
        <div class="card card-info">
          <div class="card-header">✏️ 个人信息</div>
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
                <button class="opt-btn" :class="{ active: form.gender === 'male' }" @click="form.gender = 'male'">♂ 男</button>
                <button class="opt-btn" :class="{ active: form.gender === 'female' }" @click="form.gender = 'female'">♀ 女</button>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">🎯 健身目标</div>
          <div class="goal-grid">
            <button v-for="g in goalOptions" :key="g.value"
              class="opt-btn goal-btn"
              :class="{ active: form.goal === g.value }"
              @click="form.goal = g.value">{{ g.label }}</button>
          </div>
        </div>

        <div class="card card-state">
          <div class="card-header">⚙️ 训练状态</div>
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
          <p class="day-count">共 {{ selectedDays.length }} 天/周</p>
        </div>
      </div>

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
        <p class="empty-sub">完成引导设置后显示训练周期路线图</p>
      </div>

      <TrainingKnowledgeCard />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { useCycleStore } from '@/stores/cycle'
import { saveProfileCombined } from '@/services/api'
import CycleRoadmapNew from '@/components/CycleRoadmapNew.vue'
import TrainingKnowledgeCard from '@/components/TrainingKnowledgeCard.vue'

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
  gap: 16px;
  align-items: stretch;
}

/* ── 左侧 ── */
.profile-left {
  width: 380px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 头像行 —— 紧凑横排 */
.avatar-section {
  background: #fff;
  border-radius: 14px;
  padding: 12px 16px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  border: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.avatar-icon {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  font-size: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar-info {
  flex: 1;
  min-width: 0;
}
.profile-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0;
  line-height: 1.3;
}
.profile-goal {
  font-size: 12px;
  color: #f97316;
  margin: 0;
  font-weight: 500;
}

/* 中间卡片区撑满 */
.cards-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ── 卡片 ── */
.card {
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.05);
  border: 1px solid #f0f0f0;
}
.cards-area .card {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.cards-area .card.card-state {
  flex: 1.4;
}

.card-header {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 10px;
  line-height: 1;
}

/* ── 个人信息 ── */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.field label {
  font-size: 11px;
  color: #888;
  margin-bottom: 3px;
  display: block;
}
.field input {
  width: 100%;
  border: 1.5px solid #eee;
  background: #f8f8f8;
  border-radius: 8px;
  padding: 7px 9px;
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  outline: none;
  box-sizing: border-box;
}
.field input:focus {
  border-color: #f97316;
}

/* ── 按钮 ── */
.opt-btn {
  border-radius: 8px;
  border: 1.5px solid #eee;
  background: #f8f8f8;
  color: #999;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
  padding: 6px 0;
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

.btn-pair { display: flex; gap: 6px; }
.btn-pair .opt-btn { flex: 1; }

/* ── 健身目标 ── */
.goal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  flex: 1;
  align-content: center;
}
.goal-btn {
  padding: 8px 0;
  font-size: 13px;
}

/* ── 训练状态 ── */
.state-row {
  margin-bottom: 10px;
}
.state-row:last-of-type {
  margin-bottom: 0;
}
.state-row > label {
  font-size: 11px;
  color: #888;
  margin-bottom: 3px;
  display: block;
}
.btn-triple {
  display: flex;
  gap: 5px;
}
.btn-triple .opt-btn { flex: 1; }

.day-picker {
  display: flex;
  gap: 5px;
}
.day-chip {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  border: 1.5px solid #eee;
  background: #fff;
  color: #999;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.day-chip:hover { border-color: #f97316; }
.day-chip.active { background: #f97316; border-color: #f97316; color: #fff; }

.day-count {
  font-size: 11px;
  color: #888;
  margin: 6px 0 0;
}

/* ── 保存按钮 ── */
.save-all-btn {
  width: 100%;
  padding: 11px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-sizing: border-box;
  transition: box-shadow 0.2s;
}
.save-all-btn:hover:not(:disabled) {
  box-shadow: 0 3px 10px rgba(249,115,22,0.3);
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
  gap: 12px;
}
.profile-right > :deep(.cycle-roadmap-wrap),
.profile-right > :first-child {
  flex: 1;
}

.empty-state {
  background: #fff;
  border-radius: 14px;
  padding: 30px;
  text-align: center;
  border: 1px solid #f0f0f0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.empty-state p {
  font-size: 14px;
  color: #888;
  margin: 0 0 4px;
}
.empty-sub {
  font-size: 12px;
  color: #bbb;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .profile-page { flex-direction: column; }
  .profile-left { width: 100%; }
}
</style>

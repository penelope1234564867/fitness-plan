<template>
  <div class="setup-page">
    <!-- 进度指示 -->
    <div class="progress-bar">
      <div
        v-for="(step, i) in steps"
        :key="i"
        class="progress-step"
        :class="{ active: currentIndex === i, done: currentIndex > i }"
        @click="currentIndex = i"
      >
        <div class="step-dot">
          <span v-if="currentIndex > i">✓</span>
          <span v-else>{{ i + 1 }}</span>
        </div>
        <span class="step-label">{{ step }}</span>
      </div>
    </div>

    <!-- 卡片容器 -->
    <div class="card-container">
      <transition name="card-slide" mode="out-in">
        <!-- Card 1: 身体信息 -->
        <div v-if="currentIndex === 0" key="card1" class="wizard-card">
          <div class="card-icon">👤</div>
          <h2 class="card-title">你的身体信息</h2>
          <p class="card-desc">让我先了解你的基本身体数据</p>

          <div class="card-body">
            <div class="form-grid">
              <div class="form-item">
                <label>身高 (cm)</label>
                <input
                  v-model.number="form.height"
                  type="number" min="100" max="250" placeholder="例如 175"
                  class="form-input"
                />
              </div>
              <div class="form-item">
                <label>体重 (kg)</label>
                <input
                  v-model.number="form.weight"
                  type="number" min="30" max="250" placeholder="例如 70"
                  class="form-input"
                />
              </div>
              <div class="form-item">
                <label>年龄</label>
                <input
                  v-model.number="form.age"
                  type="number" min="10" max="100" placeholder="例如 25"
                  class="form-input"
                />
              </div>
              <div class="form-item">
                <label>性别</label>
                <div class="gender-group">
                  <button
                    class="gender-btn"
                    :class="{ active: form.gender === 'male' }"
                    @click="form.gender = 'male'"
                  >♂ 男</button>
                  <button
                    class="gender-btn"
                    :class="{ active: form.gender === 'female' }"
                    @click="form.gender = 'female'"
                  >♀ 女</button>
                </div>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <button class="btn-primary" :disabled="!canGoNext" @click="nextCard">
              下一步 →
            </button>
          </div>
        </div>

        <!-- Card 2: 训练背景 -->
        <div v-else-if="currentIndex === 1" key="card2" class="wizard-card">
          <div class="card-icon">💪</div>
          <h2 class="card-title">你的训练背景</h2>
          <p class="card-desc">你的训练经验和锻炼地点</p>

          <div class="card-body">
            <label class="section-label">🏋️ 训练经验</label>
            <div class="option-row">
              <div
                v-for="opt in experienceOptions"
                :key="opt.value"
                class="option-card"
                :class="{ active: form.experience === opt.value }"
                @click="form.experience = opt.value"
              >
                <span class="option-icon">{{ opt.icon }}</span>
                <span class="option-title">{{ opt.label }}</span>
                <span class="option-desc">{{ opt.desc }}</span>
              </div>
            </div>

            <label class="section-label" style="margin-top: 20px;">📍 锻炼地点</label>
            <div class="option-row">
              <div
                v-for="loc in locationOptions"
                :key="loc.value"
                class="option-card"
                :class="{ active: form.locations.includes(loc.value) }"
                @click="toggleLocation(loc.value)"
              >
                <span class="option-icon">{{ loc.icon }}</span>
                <span class="option-title">{{ loc.label }}</span>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <button class="btn-secondary" @click="prevCard">← 上一步</button>
            <button class="btn-primary" :disabled="!canGoNext" @click="nextCard">
              下一步 →
            </button>
          </div>
        </div>

        <!-- Card 3: 训练目标 -->
        <div v-else-if="currentIndex === 2" key="card3" class="wizard-card">
          <div class="card-icon">🎯</div>
          <h2 class="card-title">你的训练目标</h2>
          <p class="card-desc">你想达到什么样的效果？</p>

          <div class="card-body">
            <div class="goal-grid">
              <div
                v-for="g in goalOptions"
                :key="g.value"
                class="goal-card"
                :class="{ active: form.goal === g.value }"
                @click="form.goal = g.value"
              >
                <span class="goal-icon-big">{{ g.icon }}</span>
                <span class="goal-label">{{ g.label }}</span>
                <span class="goal-desc">{{ g.desc }}</span>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <button class="btn-secondary" @click="prevCard">← 上一步</button>
            <button class="btn-primary" :disabled="!canGoNext" @click="nextCard">
              下一步 →
            </button>
          </div>
        </div>

        <!-- Card 4: 每周安排 -->
        <div v-else-if="currentIndex === 3" key="card4" class="wizard-card">
          <div class="card-icon">📅</div>
          <h2 class="card-title">每周安排</h2>
          <p class="card-desc">选择你每周哪几天训练</p>

          <div class="card-body">
            <label class="section-label">选择训练日</label>
            <div class="day-picker">
              <div
                v-for="d in dayOptions"
                :key="d.value"
                class="day-chip"
                :class="{ active: form.preferredDays.includes(String(d.value)) }"
                @click="toggleDay(d.value)"
              >
                {{ d.label }}
              </div>
            </div>
            <p class="day-summary">
              每周 <strong>{{ dayCount }}</strong> 天训练
            </p>
          </div>

          <div class="card-footer">
            <button class="btn-secondary" @click="prevCard">← 上一步</button>
            <button
              class="btn-generate"
              :disabled="!canGoNext || saving"
              @click="handleGenerate"
            >
              {{ saving ? '⏳ 保存中...' : '🚀 生成计划' }}
            </button>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { getProfile, createOrUpdateProfile } from '@/services/api'

const router = useRouter()
const userStore = useUserStore()

const currentIndex = ref(0)
const saving = ref(false)
const loading = ref(true)

const steps = ['身体信息', '训练背景', '训练目标', '每周安排']

const form = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
  experience: '新手',
  goal: '',
  locations: [] as string[],
  preferredDays: '1,3,5',
})

const experienceOptions = [
  { value: '新手', icon: '🌱', label: '新手', desc: '刚开始或规律训练 < 3个月' },
  { value: '中级', icon: '💪', label: '中级', desc: '规律训练 3-12个月' },
  { value: '高级', icon: '🔥', label: '高级', desc: '规律训练 > 1年' },
]

const locationOptions = [
  { value: '居家', icon: '🏠', label: '居家' },
  { value: '健身房', icon: '🏋️', label: '健身房' },
  { value: '户外', icon: '🌳', label: '户外' },
]

const goalOptions = [
  { value: '减脂', icon: '🔥', label: '减脂', desc: '降低体脂率' },
  { value: '增肌', icon: '💪', label: '增肌', desc: '增加肌肉量' },
  { value: '塑形', icon: '✨', label: '塑形', desc: '雕刻身体线条' },
  { value: '保持健康', icon: '🌿', label: '保持健康', desc: '维持运动习惯' },
]

const dayOptions = [
  { value: 1, label: '一' },
  { value: 2, label: '二' },
  { value: 3, label: '三' },
  { value: 4, label: '四' },
  { value: 5, label: '五' },
  { value: 6, label: '六' },
  { value: 7, label: '日' },
]

const dayCount = computed(() =>
  form.preferredDays.split(',').filter(Boolean).length
)

const canGoNext = computed(() => {
  switch (currentIndex.value) {
    case 0: return form.height && form.weight && form.age && form.gender
    case 1: return form.experience && form.locations.length > 0
    case 2: return !!form.goal
    case 3: return dayCount.value > 0
    default: return false
  }
})

onMounted(async () => {
  // 尝试从后端加载已有数据（重新生成时预填）
  try {
    const profile = await getProfile()
    if (profile && profile.id > 0) {
      form.height = profile.height ?? undefined
      form.weight = profile.weight ?? undefined
      form.age = profile.age ?? undefined
      form.gender = profile.gender ?? undefined
      form.experience = profile.experience || '新手'
      form.goal = profile.goal || ''
    }
  } catch {
    // 首次使用，无数据
  }

  // 从 userStore 加载训练状态
  try {
    await userStore.fetchCurrentState()
    if (userStore.currentState) {
      form.preferredDays = userStore.currentState.preferred_days || '1,3,5'
      // 保持 experience 同步
      if (!form.experience || form.experience === '新手') {
        form.experience = userStore.currentState.experience_level || '新手'
      }
    }
  } catch {
    // 首次使用，无状态
  }

  loading.value = false
})

function toggleDay(value: number) {
  const arr = form.preferredDays.split(',').map(Number).filter(Boolean)
  const idx = arr.indexOf(value)
  if (idx >= 0) {
    arr.splice(idx, 1)
  } else {
    arr.push(value)
    arr.sort()
  }
  form.preferredDays = arr.join(',')
}

function toggleLocation(value: string) {
  const idx = form.locations.indexOf(value)
  if (idx >= 0) {
    form.locations.splice(idx, 1)
  } else {
    form.locations.push(value)
  }
}

function nextCard() {
  if (currentIndex.value < steps.length - 1) {
    currentIndex.value++
  }
}

function prevCard() {
  if (currentIndex.value > 0) {
    currentIndex.value--
  }
}

async function handleGenerate() {
  saving.value = true
  try {
    // 1. 保存个人信息到后端
    await createOrUpdateProfile({
      height: form.height,
      weight: form.weight,
      age: form.age,
      gender: form.gender,
      goal: form.goal,
      experience: form.experience,
      workout_location: form.locations[0] || '居家',
    })

    // 2. 保存训练状态
    await userStore.saveCurrentState({
      experience_level: form.experience,
      workout_location: form.locations[0] || '居家',
      preferred_days: form.preferredDays,
    })

    // 3. 刷新 profile 到 store
    await userStore.fetchProfile()

    // 4. 跳转到生成页
    router.push('/generating')
  } catch (e) {
    console.error('保存失败:', e)
    alert('保存失败，请重试')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.setup-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

/* ── 进度条 ── */
.progress-bar {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 24px auto 32px;
  padding: 20px 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  width: 100%;
  max-width: 560px;
  justify-content: space-between;
}
.progress-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  flex: 1;
  position: relative;
}
.progress-step::after {
  content: '';
  position: absolute;
  top: 12px;
  left: 60%;
  width: 80%;
  height: 3px;
  background: #e8e8e8;
  z-index: 0;
}
.progress-step:last-child::after {
  display: none;
}
.progress-step.done::after {
  background: #22c55e;
}
.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: #e8e8e8;
  color: #999;
  position: relative;
  z-index: 1;
  transition: all 0.3s ease;
}
.progress-step.active .step-dot {
  background: #f97316;
  color: #fff;
  box-shadow: 0 2px 8px rgba(249,115,22,0.3);
}
.progress-step.done .step-dot {
  background: #22c55e;
  color: #fff;
}
.step-label {
  font-size: 12px;
  color: #999;
  font-weight: 500;
  white-space: nowrap;
}
.progress-step.active .step-label {
  color: #f97316;
  font-weight: 600;
}
.progress-step.done .step-label {
  color: #22c55e;
}

/* ── 卡片容器 ── */
.card-container {
  width: 100%;
  max-width: 520px;
  min-height: 480px;
}

.wizard-card {
  background: #fff;
  border-radius: 24px;
  padding: 36px 32px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
}

.card-icon {
  font-size: 48px;
  text-align: center;
  margin-bottom: 8px;
}
.card-title {
  font-size: 24px;
  font-weight: 700;
  color: #1a1a1a;
  text-align: center;
  margin: 0 0 4px 0;
}
.card-desc {
  font-size: 14px;
  color: #888;
  text-align: center;
  margin: 0 0 28px 0;
}

.card-body {
  flex: 1;
  min-height: 200px;
}

.card-footer {
  display: flex;
  gap: 12px;
  margin-top: 28px;
  justify-content: flex-end;
}

/* ── Form inputs ── */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.form-item label {
  font-size: 13px;
  font-weight: 600;
  color: #555;
}
.form-input {
  padding: 12px 14px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 500;
  outline: none;
  transition: border-color 0.2s;
  background: #fafafa;
  width: 100%;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: #f97316;
  background: #fff;
}
.form-input::placeholder {
  color: #ccc;
  font-weight: 400;
}

.gender-group {
  display: flex;
  gap: 8px;
}
.gender-btn {
  flex: 1;
  padding: 12px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  background: #fafafa;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
  color: #666;
}
.gender-btn:hover {
  border-color: #f97316;
  color: #f97316;
}
.gender-btn.active {
  border-color: #f97316;
  background: #fff7ed;
  color: #f97316;
  box-shadow: 0 2px 8px rgba(249,115,22,0.15);
}

/* ── Option cards (experience / location) ── */
.section-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #444;
  margin-bottom: 10px;
}
.option-row {
  display: flex;
  gap: 10px;
}
.option-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px 10px;
  border: 2px solid #e8e8e8;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
  text-align: center;
}
.option-card:hover {
  border-color: #f97316;
  transform: translateY(-2px);
}
.option-card.active {
  border-color: #f97316;
  background: #fff7ed;
  box-shadow: 0 4px 16px rgba(249,115,22,0.15);
}
.option-icon {
  font-size: 28px;
  margin-bottom: 6px;
}
.option-title {
  font-size: 15px;
  font-weight: 700;
  color: #333;
}
.option-desc {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
  line-height: 1.3;
}

/* ── Goal cards ── */
.goal-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.goal-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fafafa;
  text-align: center;
}
.goal-card:hover {
  border-color: #f97316;
  transform: translateY(-2px);
}
.goal-card.active {
  border-color: #f97316;
  background: #fff7ed;
  box-shadow: 0 4px 16px rgba(249,115,22,0.15);
}
.goal-icon-big {
  font-size: 40px;
  margin-bottom: 8px;
}
.goal-label {
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
}
.goal-desc {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

/* ── Day picker ── */
.day-picker {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
.day-chip {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 700;
  border: 2px solid #e8e8e8;
  background: #fafafa;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}
.day-chip:hover {
  border-color: #f97316;
  color: #f97316;
}
.day-chip.active {
  background: #f97316;
  border-color: #f97316;
  color: #fff;
  box-shadow: 0 3px 10px rgba(249,115,22,0.3);
}
.day-summary {
  text-align: center;
  font-size: 15px;
  color: #666;
  margin-top: 20px;
}

/* ── Buttons ── */
.btn-primary {
  padding: 12px 32px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #f97316, #fb923c);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(249,115,22,0.3);
  transform: translateY(-1px);
}
.btn-primary:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 12px 24px;
  border: 2px solid #e8e8e8;
  border-radius: 12px;
  background: #fff;
  color: #666;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover {
  border-color: #f97316;
  color: #f97316;
}

.btn-generate {
  padding: 12px 32px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-generate:hover:not(:disabled) {
  box-shadow: 0 4px 16px rgba(34,197,94,0.3);
  transform: translateY(-1px);
}
.btn-generate:disabled {
  background: #d9d9d9;
  cursor: not-allowed;
}

/* ── Card slide transition ── */
.card-slide-enter-active {
  animation: slideIn 0.35s ease-out;
}
.card-slide-leave-active {
  animation: slideOut 0.25s ease-in;
}
@keyframes slideIn {
  from { opacity: 0; transform: translateX(40px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes slideOut {
  from { opacity: 1; transform: translateX(0); }
  to { opacity: 0; transform: translateX(-40px); }
}
</style>

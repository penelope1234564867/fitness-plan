# ProfilePage 改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 brainstorm layout-v11 设计整合到 ProfilePage，实现统一保存接口 + 卡牌式布局 + 科学训练知识轮播

**Architecture:**
- 后端新增 `PUT /api/user/profile-combined`，在一个事务中同时更新 `User` 和 `UserCurrentState` 表
- 前端重写 ProfilePage.vue，左侧为头像+三张设置卡+统一保存，右侧为路线图+知识轮播卡
- 科学训练知识轮播独立为 `TrainingKnowledgeCard.vue` 组件

**Tech Stack:** Python FastAPI + SQLAlchemy / Vue 3 + TypeScript + Pinia

## Global Constraints

- 所有字段已存在于 `User` 表和 `UserCurrentState` 表，不新增数据库列
- 旧接口 `POST /api/user/profile` 和 `PUT /api/fitness/current-state` 保留不动
- 橙色主题色 `#f97316`
- 响应式断点 768px

---

### Task 1: Backend — ProfileCombinedRequest schema + route

**Files:**
- Modify: `backend/app/models/schemas.py` — 新增 ProfileCombinedRequest
- Modify: `backend/app/api/routes/user.py` — 新增 PUT /profile-combined

**Interfaces:**
- Consumes: 现有的 `orm_models.User`、`orm_models.UserCurrentState`
- Produces: `PUT /api/user/profile-combined` endpoint，接收 `ProfileCombinedRequest`，返回 `{"message": "保存成功"}`

- [ ] **Step 1: Add ProfileCombinedRequest to schemas.py**

在 `backend/app/models/schemas.py` 末尾新增：

```python
class ProfileCombinedRequest(BaseModel):
    """合并保存用户个人信息 + 训练状态"""
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None
    experience_level: Optional[str] = None
    workout_location: Optional[str] = None
    preferred_days: Optional[str] = None
```

- [ ] **Step 2: Add PUT /profile-combined route**

在 `backend/app/api/routes/user.py` 末尾、`create_or_update_profile` 函数之后新增：

```python
from app.models import orm_models, schemas
from app.database import get_db

@router.put("/profile-combined")
async def update_profile_combined(data: schemas.ProfileCombinedRequest,
                                   db: Session = Depends(get_db)):
    """合并保存用户个人信息 + 训练状态（一次请求更新两张表）"""
    # 1. 更新 User 表
    user = db.query(orm_models.User).first()
    if user:
        if data.height is not None:
            user.height = data.height
        if data.weight is not None:
            user.weight = data.weight
        if data.age is not None:
            user.age = data.age
        if data.gender is not None:
            user.gender = data.gender
        if data.goal is not None:
            user.goal = data.goal
    else:
        user = orm_models.User(
            height=data.height,
            weight=data.weight,
            age=data.age,
            gender=data.gender,
            goal=data.goal,
        )
        db.add(user)

    # 2. 更新 UserCurrentState 表
    ucs = db.query(orm_models.UserCurrentState).first()
    if ucs:
        if data.experience_level is not None:
            ucs.experience_level = data.experience_level
        if data.workout_location is not None:
            ucs.workout_location = data.workout_location
        if data.preferred_days is not None:
            ucs.preferred_days = data.preferred_days
    else:
        ucs = orm_models.UserCurrentState(
            experience_level=data.experience_level or "新手",
            workout_location=data.workout_location or "居家",
            preferred_days=data.preferred_days or "1,3,5",
        )
        db.add(ucs)

    db.commit()
    return {"message": "保存成功"}
```

- [ ] **Step 3: Verify with curl**

Run: 先确保后端在运行（`cd backend && python run.py &`）

```bash
curl -X PUT http://localhost:8000/api/user/profile-combined \
  -H "Content-Type: application/json" \
  -d '{"height":180,"weight":72,"age":28,"gender":"male","goal":"增肌","experience_level":"新手","workout_location":"居家","preferred_days":"1,3,5"}'
```

Expected: `{"message":"保存成功"}`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/schemas.py backend/app/api/routes/user.py
git commit -m "feat: add PUT /api/user/profile-combined for unified profile+state save"
```

---

### Task 2: Frontend types + API service

**Files:**
- Modify: `frontend/src/types/index.ts` — 新增 `ProfileCombined` 类型
- Modify: `frontend/src/services/api.ts` — 新增 `saveProfileCombined()` 方法

**Interfaces:**
- Consumes: `axios` apiClient
- Produces: `saveProfileCombined(data: ProfileCombined): Promise<void>` 供 ProfilePage 调用

- [ ] **Step 1: Add ProfileCombined type**

在 `frontend/src/types/index.ts` 中 `UserCurrentStateUpdate` 附近新增：

```typescript
export interface ProfileCombined {
  height?: number | null
  weight?: number | null
  age?: number | null
  gender?: string | null
  goal?: string | null
  experience_level?: string | null
  workout_location?: string | null
  preferred_days?: string | null
}
```

- [ ] **Step 2: Add saveProfileCombined API**

在 `frontend/src/services/api.ts` 中，`updateCurrentState` 函数之后新增：

```typescript
/** 合并保存用户个人信息 + 训练状态 */
export async function saveProfileCombined(data: ProfileCombined): Promise<void> {
  await apiClient.put('/api/user/profile-combined', data)
}
```

并确保 import 中包含 `ProfileCombined`：

```typescript
import type {
  // ... existing imports ...
  ProfileCombined,
} from '@/types'
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: add ProfileCombined type and saveProfileCombined API"
```

---

### Task 3: TrainingKnowledgeCard 组件

**Files:**
- Create: `frontend/src/components/TrainingKnowledgeCard.vue`

**Interfaces:**
- Consumes: 无（纯静态组件）
- Produces: 自包含的轮播卡片组件，供 ProfilePage 使用

- [ ] **Step 1: Create the component**

Create `frontend/src/components/TrainingKnowledgeCard.vue`:

```vue
<template>
  <div class="knowledge-card">
    <div class="knowledge-header">
      <span class="knowledge-title">📖 科学训练知识</span>
      <div class="knowledge-controls">
        <span class="slide-indicator">{{ currentSlide }}/{{ totalSlides }}</span>
        <span
          v-for="n in totalSlides" :key="n"
          class="dot"
          :class="{ active: currentSlide === n }"
          @click="goSlide(n)"
        />
      </div>
    </div>
    <div class="slides-container">
      <div class="slides-track" :style="{ transform: `translateX(-${(currentSlide - 1) * 100}%)` }">
        <!-- Slide 1: PPL -->
        <div class="slide">
          <div class="slide-icon-wrap" style="background:linear-gradient(135deg,#f97316,#fb923c);">
            <span>🏛️</span>
          </div>
          <div class="slide-title-row">
            <span class="slide-title">PPL 三分化训练</span>
            <span class="slide-badge">推 · 拉 · 腿</span>
          </div>
          <p class="slide-desc">
            本系统基于 <strong>PPL（Push / Pull / Legs）</strong> 三分化科学训练法——将训练日分为推力、拉力、腿部三个模块，
            每个模块针对特定肌群，确保每周每个部位得到足量刺激和充分恢复。
          </p>
          <div class="ppl-grid">
            <div class="ppl-item">
              <span class="ppl-icon">💥</span>
              <span class="ppl-name">Push 推力</span>
              <span class="ppl-detail">胸 · 肩 · 三头</span>
            </div>
            <div class="ppl-item">
              <span class="ppl-icon">🏋️</span>
              <span class="ppl-name">Pull 拉力</span>
              <span class="ppl-detail">背 · 二头 · 后肩</span>
            </div>
            <div class="ppl-item">
              <span class="ppl-icon">🦵</span>
              <span class="ppl-name">Legs 腿部</span>
              <span class="ppl-detail">臀 · 腿 · 核心</span>
            </div>
          </div>
        </div>
        <!-- Slide 2: 周期化 -->
        <div class="slide">
          <div class="slide-icon-wrap" style="background:linear-gradient(135deg,#22c55e,#4ade80);">
            <span>🔄</span>
          </div>
          <div class="slide-title-row">
            <span class="slide-title">周期化训练</span>
            <span class="slide-badge">四个阶段</span>
          </div>
          <p class="slide-desc">
            本系统采用 <strong>线性周期化</strong> 模型，将一个训练大周期分为四个循序渐进的阶段，
            每个阶段针对不同的训练适应目标，科学安排训练量与强度，避免平台期和过度训练。
          </p>
          <div class="phase-grid">
            <div class="phase-item">
              <span class="phase-icon">🌱</span>
              <span class="phase-name">基础适应期</span>
              <span class="phase-desc">建立神经适应与动作模式，低强度高容量</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">🔥</span>
              <span class="phase-name">肌肥大期</span>
              <span class="phase-desc">中等重量高次数，肌纤维横截面积最大化增长</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">💪</span>
              <span class="phase-name">力量提升期</span>
              <span class="phase-desc">大重量低次数，神经募集效率最大化</span>
            </div>
            <div class="phase-item">
              <span class="phase-icon">🔄</span>
              <span class="phase-name">减载恢复周</span>
              <span class="phase-desc">降低训练量，主动恢复，为下个周期储能</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const totalSlides = 2
const currentSlide = ref(1)
let timer: ReturnType<typeof setInterval> | null = null

function goSlide(n: number) {
  currentSlide.value = n
}

onMounted(() => {
  timer = setInterval(() => {
    currentSlide.value = currentSlide.value >= totalSlides ? 1 : currentSlide.value + 1
  }, 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.knowledge-card {
  background: #fff;
  border-radius: 16px;
  padding: 18px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  border: 1px solid #f0f0f0;
}
.knowledge-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.knowledge-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}
.knowledge-controls {
  margin-left: auto;
  display: flex;
  gap: 6px;
  align-items: center;
}
.slide-indicator {
  font-size: 10px;
  color: #f97316;
  font-weight: 600;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e0e0e0;
  display: inline-block;
  cursor: pointer;
  transition: background 0.2s;
}
.dot.active {
  background: #f97316;
}
.slides-container {
  overflow: hidden;
  border-radius: 12px;
}
.slides-track {
  display: flex;
  transition: transform 0.4s ease;
}
.slide {
  min-width: 100%;
  padding: 14px;
  border-radius: 12px;
  box-sizing: border-box;
}
.slide:first-child {
  background: #fffdf5;
  border: 1px solid #fde68a;
}
.slide:last-child {
  background: #fafef5;
  border: 1px solid #bbf7d0;
}
.slide-icon-wrap {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-bottom: 10px;
}
.slide-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.slide-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}
.slide-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.slide:first-child .slide-badge {
  color: #f97316;
  background: #fff7ed;
}
.slide:last-child .slide-badge {
  color: #16a34a;
  background: #f0fdf4;
}
.slide-desc {
  font-size: 12px;
  color: #555;
  line-height: 1.7;
  margin: 0 0 10px;
}
.ppl-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}
.ppl-item {
  background: #fff7ed;
  border-radius: 8px;
  padding: 8px;
  text-align: center;
  border: 1px solid #fde68a;
}
.ppl-icon { font-size: 18px; display: block; margin-bottom: 2px; }
.ppl-name { font-size: 12px; font-weight: 700; color: #92400e; display: block; }
.ppl-detail { font-size: 10px; color: #b88a6a; display: block; }

.phase-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.phase-item {
  background: #f0fdf4;
  border-radius: 8px;
  padding: 8px;
  border: 1px solid #bbf7d0;
}
.phase-icon { font-size: 14px; display: block; margin-bottom: 2px; }
.phase-name { font-size: 12px; font-weight: 700; color: #16a34a; display: block; }
.phase-desc { font-size: 10px; color: #666; line-height: 1.5; display: block; margin-top: 2px; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TrainingKnowledgeCard.vue
git commit -m "feat: add TrainingKnowledgeCard static slideshow component"
```

---

### Task 4: Rewrite ProfilePage.vue

**Files:**
- Modify: `frontend/src/views/ProfilePage.vue` — 完全重写

**Interfaces:**
- Consumes: `useUserStore`, `useCycleStore`, `saveProfileCombined` from api
- Uses: `CycleRoadmapNew`, `TrainingKnowledgeCard` components

- [ ] **Step 1: Write the new ProfilePage.vue**

完全替换 `frontend/src/views/ProfilePage.vue` 的内容：

```vue
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
  cycleStore.currentWeek?.days.filter(d => d.is_completed).length ?? 0
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
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/views/ProfilePage.vue
git commit -m "feat: rewrite ProfilePage with v11 card-based layout, unified save, and training knowledge card"
```

---

### Task 5: Verify end-to-end

- [ ] **Step 1: Restart backend**

```bash
cd backend && python run.py
```

Check for startup errors.

- [ ] **Step 2: Restart frontend**

```bash
cd frontend && npm run dev
```

Check for compile errors.

- [ ] **Step 3: Open ProfilePage**

Navigate to http://localhost:5173/#/profile (or wherever the profile route is).

Verify:
1. Left panel shows avatar, name line, personal info card, goal card, training state card, save button
2. Right panel shows CycleRoadmapNew (or empty state if no plan) + TrainingKnowledgeCard
3. Click goal / experience / location buttons → UI updates selected state
4. Click day chips → toggle on/off, day count updates
5. Click "保存全部设置" → data saved, fetch refreshed
6. Responsive: narrow browser → layout stacks vertically

- [ ] **Step 4: Commit final verification**

```bash
git add -A
git commit -m "chore: verify profile page redesign end-to-end"
```

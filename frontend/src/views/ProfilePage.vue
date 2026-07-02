<template>
  <div class="profile-page">
    <!-- 左侧：原有个人信息 -->
    <div class="profile-left">
      <div class="profile-card">
        <div class="profile-avatar">
          <span class="avatar-icon">{{ userStore.profile?.gender === 'male' ? '♂' : '♀' }}</span>
        </div>
        <h2 class="profile-name">{{ userStore.profile?.height || '?' }}cm · {{ userStore.profile?.weight || '?' }}kg</h2>
        <p class="profile-goal">{{ userStore.profile?.goal || '未设置' }}</p>

        <hr class="divider" />

        <div v-if="!editing" class="info-list">
          <div class="info-row"><span class="info-label">身高</span><span class="info-value">{{ profileData.height || '-' }} cm</span></div>
          <div class="info-row"><span class="info-label">体重</span><span class="info-value">{{ profileData.weight || '-' }} kg</span></div>
          <div class="info-row"><span class="info-label">年龄</span><span class="info-value">{{ profileData.age || '-' }} 岁</span></div>
          <div class="info-row"><span class="info-label">性别</span><span class="info-value">{{ profileData.gender === 'male' ? '男' : profileData.gender === 'female' ? '女' : '-' }}</span></div>
          <div class="info-row"><span class="info-label">目标</span><span class="info-value">{{ profileData.goal || '-' }}</span></div>
          <button class="edit-btn" @click="startEditing">✏️ 编辑个人信息</button>
        </div>

        <div v-else class="edit-form">
          <h3 class="section-title">✏️ 编辑个人信息</h3>
          <p class="section-hint">💡 修改后将用于下次生成计划</p>
          <div class="edit-row"><span class="info-label">身高 (cm)</span><input v-model.number="editData.height" type="number" min="100" max="250" class="edit-input" placeholder="165" /></div>
          <div class="edit-row"><span class="info-label">体重 (kg)</span><input v-model.number="editData.weight" type="number" min="30" max="250" class="edit-input" placeholder="65" /></div>
          <div class="edit-row"><span class="info-label">年龄</span><input v-model.number="editData.age" type="number" min="10" max="100" class="edit-input" placeholder="25" /></div>
          <div class="edit-row">
            <span class="info-label">性别</span>
            <div class="gender-group">
              <button class="gender-btn" :class="{ active: editData.gender === 'male' }" @click="editData.gender = 'male'">♂ 男</button>
              <button class="gender-btn" :class="{ active: editData.gender === 'female' }" @click="editData.gender = 'female'">♀ 女</button>
            </div>
          </div>
          <div class="edit-actions">
            <button class="cancel-btn" @click="cancelEditing">取消</button>
            <button class="save-btn" :disabled="saving" @click="handleSaveProfile">{{ saving ? '⏳ 保存中...' : '💾 保存' }}</button>
          </div>
        </div>

        <div class="state-section">
          <h3 class="section-title">⚙️ 当前训练状态</h3>
          <p class="section-hint">💡 修改后将在下周生成时生效</p>
          <div class="state-row">
            <span class="info-label">经验等级</span>
            <select v-model="stateData.experience_level" class="state-select">
              <option value="新手">🌱 新手</option>
              <option value="中级">💪 中级</option>
              <option value="高级">🔥 高级</option>
            </select>
          </div>
          <div class="state-row">
            <span class="info-label">训练地点</span>
            <select v-model="stateData.workout_location" class="state-select">
              <option value="居家">🏠 居家</option>
              <option value="健身房">🏋️ 健身房</option>
              <option value="户外">🌳 户外</option>
            </select>
          </div>
          <div class="state-row">
            <span class="info-label">训练日</span>
            <div class="day-picker-sm">
              <span v-for="d in dayOptions" :key="d.value" class="day-chip-sm" :class="{ active: stateData.preferredDays.includes(String(d.value)) }" @click="toggleDay(d.value)">{{ d.label }}</span>
            </div>
          </div>
          <p class="day-count-sm">每周 {{ stateData.preferredDays.split(',').filter(Boolean).length }} 天</p>
          <button class="save-state-btn" :disabled="stateSaving" @click="handleSaveState">{{ stateSaving ? '⏳ 保存中...' : '💾 保存训练状态' }}</button>
        </div>

        <hr class="divider" />
        <button class="regenerate-btn" @click="onRegenerate">🔄 重新生成计划</button>
      </div>
    </div>

    <!-- 右侧：训练周期总览 -->
    <div class="profile-right">
      <template v-if="cycleStore.roadmapData">
        <CycleRoadmapNew
          :data="cycleStore.roadmapData"
          :goal="cycleStore.macrocycle?.goal || '增肌'"
          :completed-days="completedDays"
          :total-days="totalDays"
          :next-phase-label="cycleStore.nextPhaseLabel ?? undefined"
        />
      </template>
      <div v-else class="profile-empty">
        <div class="empty-hint">
          <p>暂无训练计划</p>
          <p class="empty-sub">完成引导设置后，这里将显示您的训练周期路线图</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useCycleStore } from '@/stores/cycle'
import { createOrUpdateProfile } from '@/services/api'
import CycleRoadmapNew from '@/components/CycleRoadmapNew.vue'

const router = useRouter()
const userStore = useUserStore()
const cycleStore = useCycleStore()

const editing = ref(false)
const saving = ref(false)
const stateSaving = ref(false)

const dayOptions = [
  { value: 1, label: '一' }, { value: 2, label: '二' }, { value: 3, label: '三' },
  { value: 4, label: '四' }, { value: 5, label: '五' }, { value: 6, label: '六' }, { value: 7, label: '日' },
]

const profileData = computed(() => ({
  height: userStore.profile?.height,
  weight: userStore.profile?.weight,
  age: userStore.profile?.age,
  gender: userStore.profile?.gender,
  goal: userStore.profile?.goal,
}))

const editData = reactive({
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
})

const stateData = reactive({
  experience_level: '新手',
  workout_location: '居家',
  preferredDays: '1,3,5',
})

const completedDays = computed(() => cycleStore.currentWeek?.days.filter(d => d.is_completed).length ?? 0)
const totalDays = computed(() => cycleStore.currentWeek?.days.length ?? 0)

onMounted(async () => {
  await userStore.fetchProfile().catch(() => {})
  await userStore.fetchCurrentState()
  cycleStore.fetchMacrocycles().catch(() => {})

  if (userStore.profile) {
    editData.height = userStore.profile.height ?? undefined
    editData.weight = userStore.profile.weight ?? undefined
    editData.age = userStore.profile.age ?? undefined
    editData.gender = userStore.profile.gender ?? undefined
  }
  if (userStore.currentState) {
    stateData.experience_level = userStore.currentState.experience_level
    stateData.workout_location = userStore.currentState.workout_location
    stateData.preferredDays = userStore.currentState.preferred_days || stateData.preferredDays
  }
})

function startEditing() {
  editData.height = userStore.profile?.height ?? undefined
  editData.weight = userStore.profile?.weight ?? undefined
  editData.age = userStore.profile?.age ?? undefined
  editData.gender = userStore.profile?.gender ?? undefined
  editing.value = true
}
function cancelEditing() { editing.value = false }

async function handleSaveProfile() {
  saving.value = true
  try {
    await createOrUpdateProfile({
      height: editData.height, weight: editData.weight, age: editData.age,
      gender: editData.gender, goal: userStore.profile?.goal,
      experience: userStore.profile?.experience, city: userStore.profile?.city,
      workout_location: userStore.profile?.workout_location,
      days_per_week: userStore.profile?.days_per_week,
    })
    await userStore.fetchProfile()
    editing.value = false
  } catch {} finally { saving.value = false }
}

function toggleDay(value: number) {
  const arr = stateData.preferredDays.split(',').map(Number).filter(Boolean)
  const idx = arr.indexOf(value)
  if (idx >= 0) arr.splice(idx, 1)
  else { arr.push(value); arr.sort() }
  stateData.preferredDays = arr.join(',')
}

async function handleSaveState() {
  stateSaving.value = true
  try {
    await userStore.saveCurrentState({
      experience_level: stateData.experience_level,
      workout_location: stateData.workout_location,
      preferred_days: stateData.preferredDays,
    })
  } catch {} finally { stateSaving.value = false }
}

function onRegenerate() { router.push('/?force=true') }
</script>

<style scoped>
.profile-page { display: flex; gap: 20px; max-width: 900px; margin: 0 auto; padding: 20px; align-items: flex-start; }
.profile-left { width: 380px; flex-shrink: 0; }
.profile-right { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.profile-empty { background: #fff; border-radius: 14px; padding: 40px; text-align: center; border: 1px solid #f0f0f0; }
.empty-hint p { font-size: 15px; color: #888; margin: 0 0 8px; }
.empty-sub { font-size: 13px; color: #bbb; }

@media (max-width: 768px) {
  .profile-page { flex-direction: column; }
  .profile-left { width: 100%; }
}

.profile-card { background: #fff; border-radius: 20px; padding: 32px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
.profile-avatar { text-align: center; margin-bottom: 12px; }
.avatar-icon { display: inline-flex; width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, #f97316, #fb923c); color: #fff; font-size: 28px; align-items: center; justify-content: center; }
.profile-name { text-align: center; font-size: 22px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.profile-goal { text-align: center; font-size: 14px; color: #f97316; font-weight: 500; margin: 0; }
.divider { border: none; border-top: 1px solid #f0f0f0; margin: 20px 0; }
.info-list { display: flex; flex-direction: column; gap: 12px; }
.info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.info-row:last-child { border-bottom: none; }
.info-label { font-size: 14px; color: #888; }
.info-value { font-size: 14px; font-weight: 600; color: #333; }
.edit-btn { width: 100%; margin-top: 12px; padding: 10px; border-radius: 10px; border: 1px solid #f97316; background: #fff; color: #f97316; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.edit-btn:hover { background: #fff7ed; }
.edit-form { display: flex; flex-direction: column; gap: 14px; }
.section-title { font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px 0; }
.section-hint { font-size: 12px; color: #f97316; margin: 0 0 8px 0; }
.edit-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.edit-input { width: 120px; padding: 8px 12px; border: 1.5px solid #e8e8e8; border-radius: 8px; font-size: 14px; text-align: right; outline: none; transition: border-color 0.2s; }
.edit-input:focus { border-color: #f97316; }
.gender-group { display: flex; gap: 6px; }
.gender-btn { padding: 6px 14px; border: 1.5px solid #e8e8e8; border-radius: 8px; background: #fff; font-size: 14px; cursor: pointer; transition: all 0.2s; }
.gender-btn:hover { border-color: #f97316; }
.gender-btn.active { border-color: #f97316; background: #fff7ed; color: #f97316; font-weight: 600; }
.edit-actions { display: flex; gap: 10px; margin-top: 4px; }
.cancel-btn { flex: 1; padding: 10px; border: 1.5px solid #e8e8e8; border-radius: 10px; background: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }
.cancel-btn:hover { border-color: #999; }
.save-btn { flex: 1; padding: 10px; border-radius: 10px; border: none; background: linear-gradient(135deg, #f97316, #fb923c); color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }
.save-btn:hover:not(:disabled) { box-shadow: 0 4px 14px rgba(249,115,22,0.3); }
.save-btn:disabled { background: #d9d9d9; cursor: not-allowed; }
.state-section { margin: 16px 0; }
.state-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f5f5f5; }
.state-select { padding: 6px 12px; border: 1px solid #e8e8e8; border-radius: 8px; font-size: 14px; background: #fff; cursor: pointer; }
.day-picker-sm { display: flex; gap: 4px; }
.day-chip-sm { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; border: 1.5px solid #e8e8e8; background: #fff; cursor: pointer; transition: all 0.15s; user-select: none; }
.day-chip-sm:hover { border-color: #f97316; }
.day-chip-sm.active { background: #f97316; border-color: #f97316; color: #fff; }
.day-count-sm { font-size: 12px; color: #888; margin: 8px 0 12px; }
.save-state-btn { width: 100%; padding: 10px; border-radius: 10px; border: none; font-size: 14px; font-weight: 600; background: linear-gradient(135deg, #f97316, #fb923c); color: #fff; cursor: pointer; transition: all 0.2s; }
.save-state-btn:hover:not(:disabled) { box-shadow: 0 4px 14px rgba(249,115,22,0.3); }
.save-state-btn:disabled { background: #d9d9d9; cursor: not-allowed; }
.regenerate-btn { width: 100%; padding: 12px; border-radius: 12px; border: 1.5px solid #22c55e; background: #fff; color: #22c55e; font-size: 15px; font-weight: 600; cursor: pointer; }
.regenerate-btn:hover { background: #f0fdf4; }
</style>

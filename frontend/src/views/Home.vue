<template>
  <div class="home-container">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="icon-wrapper">
        <span class="icon">💪</span>
      </div>
      <h1 class="page-title">AI 智能健身助手</h1>
      <p class="page-subtitle">输入你的健身目标，AI 将为你定制专属训练计划</p>
    </div>

    <a-card class="form-card" :bordered="false">
      <a-form :model="formData" layout="vertical" @finish="handleSubmit">
        <!-- 第一步：个人资料 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">👤</span>
            <span class="section-title">个人资料</span>
          </div>
          <a-row :gutter="16">
            <a-col :span="6">
              <a-form-item label="身高 (cm)" name="height">
                <a-input-number
                  v-model:value="formData.height"
                  :min="100"
                  :max="250"
                  style="width: 100%"
                  placeholder="例如: 175"
                />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="体重 (kg)" name="weight">
                <a-input-number
                  v-model:value="formData.weight"
                  :min="30"
                  :max="250"
                  style="width: 100%"
                  placeholder="例如: 70"
                />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="年龄" name="age">
                <a-input-number
                  v-model:value="formData.age"
                  :min="10"
                  :max="100"
                  style="width: 100%"
                  placeholder="例如: 25"
                />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="性别" name="gender">
                <a-select v-model:value="formData.gender" placeholder="请选择">
                  <a-select-option value="male">♂ 男</a-select-option>
                  <a-select-option value="female">♀ 女</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第二步：健身目标 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">🎯</span>
            <span class="section-title">健身目标</span>
          </div>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item
                label="训练目标"
                name="goal"
                :rules="[{ required: true, message: '请选择训练目标' }]"
              >
                <a-select v-model:value="formData.goal" size="large" placeholder="选择目标">
                  <a-select-option value="减脂">🔥 减脂</a-select-option>
                  <a-select-option value="增肌">💪 增肌</a-select-option>
                  <a-select-option value="塑形">✨ 塑形</a-select-option>
                  <a-select-option value="保持健康">🌿 保持健康</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item
                label="经验水平"
                name="experience_level"
                :rules="[{ required: true, message: '请选择经验水平' }]"
              >
                <a-select v-model:value="formData.experience_level" size="large" placeholder="选择水平">
                  <a-select-option value="新手">🌱 新手</a-select-option>
                  <a-select-option value="中级">📈 中级</a-select-option>
                  <a-select-option value="高级">🏆 高级</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item
                label="锻炼地点"
                name="workout_location"
                :rules="[{ required: true, message: '请选择锻炼地点' }]"
              >
                <a-select v-model:value="formData.workout_location" size="large" placeholder="选择地点">
                  <a-select-option value="健身房">🏋️ 健身房</a-select-option>
                  <a-select-option value="居家">🏠 居家</a-select-option>
                  <a-select-option value="户外">🌳 户外</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第三步：计划参数 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">⚙️</span>
            <span class="section-title">计划参数</span>
          </div>
          <a-row :gutter="16">
            <a-col :span="6">
              <a-form-item
                label="每周训练天数"
                name="days_per_week"
                :rules="[{ required: true, message: '请选择天数' }]"
              >
                <a-select v-model:value="formData.days_per_week" size="large">
                  <a-select-option :value="2">2 天</a-select-option>
                  <a-select-option :value="3">3 天</a-select-option>
                  <a-select-option :value="4">4 天</a-select-option>
                  <a-select-option :value="5">5 天</a-select-option>
                  <a-select-option :value="6">6 天</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item
                label="计划持续周数"
                name="duration_weeks"
                :rules="[{ required: true, message: '请选择周数' }]"
              >
                <a-select v-model:value="formData.duration_weeks" size="large">
                  <a-select-option :value="2">2 周</a-select-option>
                  <a-select-option :value="4">4 周</a-select-option>
                  <a-select-option :value="8">8 周</a-select-option>
                  <a-select-option :value="12">12 周</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="饮食偏好" name="diet_preference">
                <a-select v-model:value="formData.diet_preference" size="large">
                  <a-select-option value="普通">🍚 普通</a-select-option>
                  <a-select-option value="高蛋白">🥩 高蛋白</a-select-option>
                  <a-select-option value="低碳水">🥗 低碳水</a-select-option>
                  <a-select-option value="素食">🥬 素食</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="所在城市（天气参考）" name="city">
                <a-input v-model:value="formData.city" placeholder="例如: 北京" />
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第四步：额外要求 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">💬</span>
            <span class="section-title">额外要求</span>
          </div>
          <a-form-item name="notes">
            <a-textarea
              v-model:value="formData.notes"
              placeholder="特殊需求或备注（例如：膝盖不好、时间有限、有氧偏好等）"
              :rows="3"
              size="large"
            />
          </a-form-item>
        </div>

        <!-- 提交按钮 -->
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="generating"
            size="large"
            block
            class="submit-button"
          >
            <template v-if="!generating">
              <span class="button-icon">🚀</span>
              <span>生成我的训练计划</span>
            </template>
            <template v-else>
              <span>AI 正在生成个性化计划...</span>
            </template>
          </a-button>
        </a-form-item>

        <!-- 生成进度 -->
        <a-form-item v-if="generating">
          <div class="loading-container">
            <a-progress
              :percent="loadingProgress"
              status="active"
              :stroke-color="{
                '0%': '#52c41a',
                '100%': '#1890ff',
              }"
              :stroke-width="10"
            />
            <p class="loading-status">{{ loadingStatus }}</p>
          </div>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePlanStore } from '@/stores/plan'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const planStore = usePlanStore()
const userStore = useUserStore()

const generating = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = reactive({
  goal: undefined as string | undefined,
  experience_level: undefined as string | undefined,
  workout_location: undefined as string | undefined,
  days_per_week: 3,
  duration_weeks: 4,
  diet_preference: '普通',
  city: '',
  notes: '',
  height: undefined as number | undefined,
  weight: undefined as number | undefined,
  age: undefined as number | undefined,
  gender: undefined as string | undefined,
})

const handleSubmit = async () => {
  generating.value = true
  loadingProgress.value = 0
  loadingStatus.value = '🚀 正在初始化...'

  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 8
      if (loadingProgress.value <= 30) {
        loadingStatus.value = '📋 正在分析你的健身目标...'
      } else if (loadingProgress.value <= 50) {
        loadingStatus.value = '🏋️ 正在搜索适合的训练动作...'
      } else if (loadingProgress.value <= 70) {
        loadingStatus.value = '🌤️ 正在查询天气和编排日程...'
      } else {
        loadingStatus.value = '📝 正在汇总生成完整计划...'
      }
    }
  }, 600)

  try {
    // 如果有用户资料，先保存
    if (formData.height || formData.weight || formData.age || formData.gender) {
      await userStore.saveProfile({
        height: formData.height,
        weight: formData.weight,
        age: formData.age,
        gender: formData.gender,
        goal: formData.goal,
        experience: formData.experience_level,
      }).catch(() => { /* 非关键步骤 */ })
    }

    // 生成计划
    await planStore.createPlan({
      goal: formData.goal!,
      experience_level: formData.experience_level!,
      workout_location: formData.workout_location!,
      days_per_week: Number(formData.days_per_week),
      duration_weeks: Number(formData.duration_weeks),
      diet_preference: formData.diet_preference,
      city: formData.city || undefined,
      notes: formData.notes,
    })

    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '✅ 训练计划生成成功！'

    message.success('训练计划生成成功！')
    setTimeout(() => {
      router.push('/plan')
    }, 800)
  } catch (error: any) {
    clearInterval(progressInterval)
    message.error(error.message || '生成失败，请稍后重试')
  } finally {
    setTimeout(() => {
      generating.value = false
      loadingProgress.value = 0
      loadingStatus.value = ''
    }, 1000)
  }
}
</script>

<style scoped>
.home-container {
  min-height: calc(100vh - 64px);
  background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
  padding: 40px 20px 60px;
  position: relative;
  overflow: hidden;
}

.bg-decoration {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 20s infinite ease-in-out;
}
.circle-1 { width: 300px; height: 300px; top: -100px; left: -100px; animation-delay: 0s; }
.circle-2 { width: 200px; height: 200px; top: 50%; right: -50px; animation-delay: 5s; }
.circle-3 { width: 150px; height: 150px; bottom: -50px; left: 30%; animation-delay: 10s; }

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(180deg); }
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
  animation: fadeInDown 0.8s ease-out;
  position: relative;
  z-index: 1;
}
.icon-wrapper { margin-bottom: 16px; }
.icon { font-size: 72px; display: inline-block; animation: bounce 2s infinite; }

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-16px); }
}

.page-title {
  font-size: 48px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
  text-shadow: 2px 2px 6px rgba(0,0,0,0.3);
}
.page-subtitle {
  font-size: 18px;
  color: rgba(255,255,255,0.95);
  margin: 0;
  font-weight: 300;
}

.form-card {
  max-width: 1100px;
  margin: 0 auto;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  animation: fadeInUp 0.8s ease-out;
  position: relative;
  z-index: 1;
}

.form-section {
  margin-bottom: 24px;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
  border-radius: 14px;
  border: 1px solid #e8e8e8;
  transition: all 0.3s ease;
}
.form-section:hover {
  box-shadow: 0 6px 20px rgba(0, 176, 155, 0.12);
  transform: translateY(-1px);
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 2px solid #00b09b;
}
.section-icon { font-size: 22px; margin-right: 10px; }
.section-title { font-size: 17px; font-weight: 600; color: #333; }

.submit-button {
  height: 54px;
  border-radius: 27px;
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
  border: none;
  box-shadow: 0 6px 20px rgba(0, 176, 155, 0.4);
  transition: all 0.3s ease;
}
.submit-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(0, 176, 155, 0.5);
}
.button-icon { margin-right: 8px; font-size: 20px; }

.loading-container {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #fff 100%);
  border-radius: 14px;
  border: 2px dashed #00b09b;
}
.loading-status { margin-top: 12px; color: #00b09b; font-size: 16px; font-weight: 500; }

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-30px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

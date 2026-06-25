import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  generatePlan,
  getPlans,
  getPlan,
} from '@/services/api'
import type {
  PlanRequest,
  FitnessPlan,
  FitnessPlanSummary,
  ExerciseItem,
  DayPlan,
} from '@/types'
import dayjs from 'dayjs'

export const useWorkoutStore = defineStore('workout', () => {
  // ── 计划数据 ──
  const currentPlan = ref<FitnessPlan | null>(null)
  const planList = ref<FitnessPlanSummary[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ── 生成状态 ──
  const isGenerating = ref(false)
  const generationProgress = ref(0)
  const generationStatus = ref('')

  // ── 日历数据 ──
  const currentMonth = ref(dayjs().format('YYYY-MM'))
  const dayPlans = ref<Map<string, DayPlan>>(new Map())

  /** 当前日历年月显示 */
  const monthLabel = computed(() => {
    return dayjs(currentMonth.value).format('YYYY年M月')
  })

  /** 当前月天数 */
  const daysInMonth = computed(() => {
    return dayjs(currentMonth.value).daysInMonth()
  })

  /** 当前月第一天是星期几 (0=周日) */
  const firstDayOfWeek = computed(() => {
    return dayjs(currentMonth.value + '-01').day()
  })

  // ── 生成计划 ──

  async function createPlan(request: PlanRequest) {
    isGenerating.value = true
    generationProgress.value = 0
    error.value = null

    try {
      // 模拟进度动画
      const progressTimer = setInterval(() => {
        if (generationProgress.value < 90) {
          generationProgress.value += 10
          if (generationProgress.value <= 30) {
            generationStatus.value = '📋 分析你的健身目标...'
          } else if (generationProgress.value <= 50) {
            generationStatus.value = '🏋️ 搜索适合的训练动作...'
          } else if (generationProgress.value <= 70) {
            generationStatus.value = '📅 编排训练日程...'
          } else {
            generationStatus.value = '📝 生成完整计划...'
          }
        }
      }, 500)

      const result = await generatePlan(request)

      clearInterval(progressTimer)
      generationProgress.value = 100
      generationStatus.value = '✅ 计划生成成功！'

      if (result?.id) {
        currentPlan.value = result as FitnessPlan
        buildDayPlans(result as FitnessPlan)
      }

      if (result?.id) {
        localStorage.setItem('fitness_current_plan_id', String(result.id))
      }

      return result
    } catch (e: any) {
      error.value = e.message || '生成计划失败'
      throw e
    } finally {
      setTimeout(() => {
        isGenerating.value = false
      }, 800)
    }
  }

  // ── 构建日历数据 ──

  function buildDayPlans(plan: FitnessPlan) {
    const map = new Map<string, DayPlan>()

    if (!plan.weekly_plans) return

    const dayOffsets: Record<string, number> = {
      '周一': 0, '周二': 1, '周三': 2, '周四': 3,
      '周五': 4, '周六': 5, '周日': 6,
    }

    for (const week of plan.weekly_plans) {
      if (!week.days) continue

      for (const day of week.days) {
        const offset = dayOffsets[day.day]
        if (offset === undefined) continue

        const weekOffset = (week.week - 1) * 7
        const planStart = dayjs(plan.created_at || undefined).startOf('week')
        const date = planStart.add(weekOffset + offset, 'day')
        const dateStr = date.format('YYYY-MM-DD')

        const isRestDay = day.focus === '休息' || day.main?.length === 0

        const dayPlan: DayPlan = {
          date: dateStr,
          dayOfWeek: date.day(),
          focusArea: day.focus || '训练',
          isRestDay,
          sections: [],
        }

        if (!isRestDay) {
          if (day.warmup?.length) {
            dayPlan.sections.push({
              type: 'warmup',
              label: '🔥 热身',
              exercises: day.warmup.map((ex: ExerciseItem, i: number) => ({
                name: ex.name,
                targetMuscle: ex.target_muscle,
                category: ex.category,
                sets: ex.sets,
                reps: ex.reps,
                weight: ex.weight_suggestion,
                duration: 30,
                completed: false,
                tooHeavy: false,
                order: i + 1,
                imageUrl: (ex as any).image_url,
                description: (ex as any).description,
              })),
            })
          }

          if (day.main?.length) {
            dayPlan.sections.push({
              type: 'main',
              label: '💪 主训练',
              exercises: day.main.map((ex: ExerciseItem, i: number) => ({
                name: ex.name,
                targetMuscle: ex.target_muscle,
                category: ex.category,
                sets: ex.sets,
                reps: ex.reps,
                weight: ex.weight_suggestion,
                completed: false,
                tooHeavy: false,
                order: i + 1,
                imageUrl: (ex as any).image_url,
                description: (ex as any).description,
              })),
            })
          }

          if (day.cooldown?.length) {
            dayPlan.sections.push({
              type: 'cooldown',
              label: '🧘 拉伸',
              exercises: day.cooldown.map((ex: ExerciseItem, i: number) => ({
                name: ex.name,
                targetMuscle: ex.target_muscle,
                category: ex.category,
                sets: ex.sets,
                reps: ex.reps,
                weight: ex.weight_suggestion,
                duration: 30,
                completed: false,
                tooHeavy: false,
                order: i + 1,
                imageUrl: (ex as any).image_url,
                description: (ex as any).description,
              })),
            })
          }
        }

        map.set(dateStr, dayPlan)
      }
    }

    dayPlans.value = map
  }

  // ── 获取某天计划 ──

  function getDayPlan(date: string): DayPlan | undefined {
    return dayPlans.value.get(date)
  }

  /** 获取某天的训练状态 */
  function getDayStatus(
    date: string,
  ): 'rest' | 'pending' | 'partial' | 'completed' | 'missed' | 'future' {
    const plan = dayPlans.value.get(date)
    if (!plan) return 'pending'
    if (plan.isRestDay) return 'rest'

    const today = dayjs().format('YYYY-MM-DD')
    if (date > today) return 'future'

    const allExercises = plan.sections.flatMap(s => s.exercises)
    if (allExercises.length === 0) return 'pending'

    const doneCount = allExercises.filter(e => e.completed).length
    if (doneCount === 0) return 'pending'
    if (doneCount >= allExercises.length) return 'completed'
    return 'partial'
  }

  // ── 切换打勾状态 ──

  function toggleExercise(date: string, sectionIdx: number, exerciseIdx: number) {
    const plan = dayPlans.value.get(date)
    if (!plan) return

    const exercise = plan.sections[sectionIdx]?.exercises[exerciseIdx]
    if (!exercise) return

    exercise.completed = !exercise.completed
    if (!exercise.completed) {
      exercise.tooHeavy = false
    }

    // 持久化到 localStorage
    const key = `ex_${date}_${sectionIdx}_${exerciseIdx}`
    localStorage.setItem(key, JSON.stringify({
      c: exercise.completed,
      h: exercise.tooHeavy,
    }))
  }

  /** 记录「太重了」 */
  function markTooHeavy(date: string, sectionIdx: number, exerciseIdx: number) {
    const plan = dayPlans.value.get(date)
    if (!plan) return

    const exercise = plan.sections[sectionIdx]?.exercises[exerciseIdx]
    if (!exercise) return

    exercise.tooHeavy = true

    const key = `ex_${date}_${sectionIdx}_${exerciseIdx}`
    localStorage.setItem(key, JSON.stringify({
      c: exercise.completed,
      h: exercise.tooHeavy,
    }))
  }

  /** 从 localStorage 恢复完成状态 */
  function restoreLocalState(date: string) {
    const plan = dayPlans.value.get(date)
    if (!plan) return

    for (let si = 0; si < plan.sections.length; si++) {
      for (let ei = 0; ei < plan.sections[si].exercises.length; ei++) {
        const key = `ex_${date}_${si}_${ei}`
        const saved = localStorage.getItem(key)
        if (saved) {
          try {
            const state = JSON.parse(saved)
            plan.sections[si].exercises[ei].completed = state.c
            plan.sections[si].exercises[ei].tooHeavy = state.h
          } catch { /* ignore */ }
        }
      }
    }
  }

  // ── 计划列表操作 ──

  async function fetchPlans() {
    loading.value = true
    try {
      planList.value = await getPlans()
      return planList.value
    } finally {
      loading.value = false
    }
  }

  async function fetchPlan(id: number) {
    loading.value = true
    try {
      const plan = await getPlan(id)
      currentPlan.value = plan
      buildDayPlans(plan)
      return plan
    } finally {
      loading.value = false
    }
  }

  function clearCurrent() {
    currentPlan.value = null
    dayPlans.value = new Map()
  }

  // ── 示例数据（前端预览用） ──

  function loadDemoData() {
    const today = dayjs()
    const startOfWeek = today.startOf('week')

    const demoPlan: FitnessPlan = {
      id: 999,
      goal: '减脂',
      experience_level: '新手',
      workout_location: '居家',
      days_per_week: 3,
      duration_weeks: 4,
      diet_preference: '普通',
      created_at: today.format('YYYY-MM-DD'),
      weekly_plans: [
        {
          week: 1,
          days: [
            {
              day: '周一', focus: '腿部训练',
              warmup: [
                { name: '开合跳', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/124/Jumping-jacks-1.png', description: '站立姿势，双脚并拢，双手放在身体两侧。跳起时双脚向外张开，同时双手向上举过头顶。落地时双脚并拢，双手回到身体两侧。保持均匀呼吸，节奏稳定。' },
                { name: '高抬腿', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/126/High-knees-1.png', description: '站立姿势，交替抬起膝盖至腰部高度，同时摆动双臂。保持背部挺直，核心收紧，快速交替进行。' },
              ],
              main: [
                { name: '徒手深蹲', target_muscle: '大腿', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/96/Bodyweight-squat-1.png', description: '双脚与肩同宽站立，脚尖微微向外。保持背部挺直，屈膝下蹲至大腿与地面平行。膝盖不要超过脚尖，重心放在脚跟。起身时呼气，下蹲时吸气。' },
                { name: '弓步蹲', target_muscle: '大腿', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/98/Lunges-1.png', description: '站立姿势，一脚向前迈出一大步，屈膝下蹲至前后腿均呈90度。前腿膝盖不超过脚尖，后腿膝盖接近地面。交替进行，保持上半身挺直。' },
                { name: '臀桥', target_muscle: '臀部', sets: 3, reps: 15, category: 'strength', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/103/Glute-bridge-1.png', description: '仰卧，双膝弯曲，双脚平放在地面，手臂放在身体两侧。收紧臀部和核心，将臀部向上抬起至身体呈一直线。在顶部停顿1-2秒，然后缓慢放下。' },
                { name: '蚌式开合', target_muscle: '臀部', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/101/Clamshell-1.png', description: '侧卧，双膝弯曲成90度，双脚并拢。保持双脚接触，将上方的膝盖向上打开，像蚌壳一样。在顶部停顿，然后缓慢放下。两侧交替进行。' },
              ],
              cooldown: [
                { name: '大腿前侧拉伸', target_muscle: '大腿', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
                { name: '臀部拉伸', target_muscle: '臀部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
              ],
            },
            {
              day: '周二', focus: '休息',
              warmup: [], main: [], cooldown: [],
            },
            {
              day: '周三', focus: '上肢训练',
              warmup: [
                { name: '肩部环绕', target_muscle: '肩部', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/127/Shoulder-circles-1.png', description: '站立姿势，双臂向两侧伸直。以肩关节为轴心，双臂向前画圈10次，再向后画圈10次。保持缓慢均匀的呼吸。' },
                { name: '手臂摆动', target_muscle: '手臂', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/128/Arm-swings-1.png', description: '站立姿势，双臂自然垂于身体两侧。交替向前摆动双臂，幅度逐渐增大，激活肩部和背部肌肉。' },
              ],
              main: [
                { name: '俯卧撑', target_muscle: '胸部', sets: 3, reps: 10, category: 'strength', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/88/Push-up-1.png', description: '俯卧姿势，双手略宽于肩，身体呈一直线。屈肘下降身体至胸部接近地面，然后用力推起至起始位置。保持核心收紧，不要塌腰或撅臀。' },
                { name: '弹力带划船', target_muscle: '背部', sets: 3, reps: 12, category: 'strength', weight_suggestion: '弹力带', image_url: 'https://wger.de/media/exercise-images/89/Bent-over-row-1.png', description: '将弹力带固定于脚底，屈膝俯身，保持背部挺直。双手抓住弹力带两端，屈肘将手臂向后拉，肩胛骨收紧。缓慢回到起始位置。' },
                { name: '平板支撑', target_muscle: '核心', sets: 3, reps: 1, duration: 30, category: 'core', weight_suggestion: '自重', image_url: 'https://wger.de/media/exercise-images/107/Plank-1.png', description: '俯卧，前臂撑地，肘部在肩膀正下方。身体呈一直线，收紧核心和臀部。保持姿势，均匀呼吸，不要塌腰或抬头。' },
              ],
              cooldown: [
                { name: '胸部拉伸', target_muscle: '胸部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
                { name: '背部拉伸', target_muscle: '背部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
              ],
            },
            {
              day: '周四', focus: '休息',
              warmup: [], main: [], cooldown: [],
            },
            {
              day: '周五', focus: '核心+有氧',
              warmup: [
                { name: '开合跳', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重' },
                { name: '原地踏步', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重' },
              ],
              main: [
                { name: '卷腹', target_muscle: '腹部', sets: 3, reps: 15, category: 'core', weight_suggestion: '自重' },
                { name: '登山跑', target_muscle: '核心', sets: 3, reps: 1, duration: 30, category: 'cardio', weight_suggestion: '自重' },
                { name: '俄罗斯转体', target_muscle: '腹部', sets: 3, reps: 16, category: 'core', weight_suggestion: '自重' },
                { name: '高抬腿', target_muscle: '全身', sets: 3, reps: 1, duration: 30, category: 'cardio', weight_suggestion: '自重' },
              ],
              cooldown: [
                { name: '腹部拉伸', target_muscle: '腹部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
                { name: '全身放松', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' },
              ],
            },
            {
              day: '周六', focus: '休息',
              warmup: [], main: [], cooldown: [],
            },
            {
              day: '周日', focus: '休息',
              warmup: [], main: [], cooldown: [],
            },
          ],
        },
        // 第2周同第1周
        {
          week: 2,
          days: [
            { day: '周一', focus: '腿部训练', warmup: [{ name: '开合跳', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重' }], main: [{ name: '深蹲', target_muscle: '大腿', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重' }, { name: '弓步蹲', target_muscle: '大腿', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重' }, { name: '臀桥', target_muscle: '臀部', sets: 3, reps: 15, category: 'strength', weight_suggestion: '自重' }, { name: '蚌式开合', target_muscle: '臀部', sets: 3, reps: 12, category: 'strength', weight_suggestion: '自重' }], cooldown: [{ name: '拉伸', target_muscle: '大腿', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' }] },
            { day: '周二', focus: '休息', warmup: [], main: [], cooldown: [] },
            { day: '周三', focus: '上肢训练', warmup: [{ name: '肩部环绕', target_muscle: '肩部', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重' }], main: [{ name: '俯卧撑', target_muscle: '胸部', sets: 3, reps: 10, category: 'strength', weight_suggestion: '自重' }, { name: '弹力带划船', target_muscle: '背部', sets: 3, reps: 12, category: 'strength', weight_suggestion: '弹力带' }], cooldown: [{ name: '拉伸', target_muscle: '胸部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' }] },
            { day: '周四', focus: '休息', warmup: [], main: [], cooldown: [] },
            { day: '周五', focus: '核心+有氧', warmup: [{ name: '开合跳', target_muscle: '全身', sets: 1, reps: 1, duration: 30, category: 'warmup', weight_suggestion: '自重' }], main: [{ name: '卷腹', target_muscle: '腹部', sets: 3, reps: 15, category: 'core', weight_suggestion: '自重' }, { name: '登山跑', target_muscle: '核心', sets: 3, reps: 1, duration: 30, category: 'cardio', weight_suggestion: '自重' }, { name: '俄罗斯转体', target_muscle: '腹部', sets: 3, reps: 16, category: 'core', weight_suggestion: '自重' }], cooldown: [{ name: '拉伸', target_muscle: '腹部', sets: 1, reps: 1, duration: 30, category: 'stretch', weight_suggestion: '' }] },
            { day: '周六', focus: '休息', warmup: [], main: [], cooldown: [] },
            { day: '周日', focus: '休息', warmup: [], main: [], cooldown: [] },
          ],
        },
      ],
    }

    currentPlan.value = demoPlan
    buildDayPlans(demoPlan)
    localStorage.setItem('fitness_demo_mode', 'true')
  }

  // ── 月份导航 ──

  function prevMonth() {
    currentMonth.value = dayjs(currentMonth.value).subtract(1, 'month').format('YYYY-MM')
  }

  function nextMonth() {
    currentMonth.value = dayjs(currentMonth.value).add(1, 'month').format('YYYY-MM')
  }

  function goToToday() {
    currentMonth.value = dayjs().format('YYYY-MM')
  }

  return {
    currentPlan,
    planList,
    loading,
    error,
    isGenerating,
    generationProgress,
    generationStatus,
    currentMonth,
    dayPlans,
    monthLabel,
    daysInMonth,
    firstDayOfWeek,
    createPlan,
    fetchPlans,
    fetchPlan,
    clearCurrent,
    getDayPlan,
    getDayStatus,
    toggleExercise,
    markTooHeavy,
    restoreLocalState,
    loadDemoData,
    prevMonth,
    nextMonth,
    goToToday,
  }
})

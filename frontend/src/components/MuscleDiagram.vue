<template>
  <div class="muscle-diagram">
    <div class="diagram-header">
      <span class="diagram-title">💪 肌肉分布</span>
    </div>

    <div class="diagram-body">
      <HumanAnatomy
        :gender="gender || 'male'"
        :selected-primary-muscle-groups="primaryGroups"
        :selected-secondary-muscle-groups="secondaryGroups"
        primary-highlight-color="#fb923c"
        secondary-highlight-color="#fdba74"
        default-muscle-color="#e5e5e5"
        background-color="#ffffff"
        :primary-opacity="0.8"
        :secondary-opacity="0.5"
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { HumanMuscleAnatomy as HumanAnatomy } from '@lucawahlen/vue-human-muscle-anatomy'

const props = defineProps<{
  gender?: 'male' | 'female'
  primaryMuscles?: { id: number; name_en: string; name_cn: string }[]
  secondaryMuscles?: { id: number; name_en: string; name_cn: string }[]
}>()

/**
 * wger 肌肉 ID → vue-human-muscle-anatomy 肌群名映射
 */
const WGER_TO_MUSCLE_GROUP: Record<number, string> = {
  1:  'biceps',       // 肱二头肌
  2:  'frontDelts',   // 三角肌（默认前束，推类为主）
  3:  'lowerBack',    // 竖脊肌
  4:  'chest',        // 胸大肌
  5:  'triceps',      // 肱三头肌
  6:  'abs',          // 腹肌
  8:  'glutes',       // 臀大肌
  9:  'traps',        // 斜方肌
  10: 'quads',        // 股四头肌
  11: 'hamstrings',   // 腘绳肌
  12: 'lats',         // 背阔肌
  13: 'calves',       // 小腿
  14: 'forearms',     // 前臂
}

/** 将 wger 肌肉列表转为 vue-human-muscle-anatomy 肌群名数组 */
function toGroups(muscles: { id: number }[]): string[] {
  return muscles
    .map(m => WGER_TO_MUSCLE_GROUP[m.id])
    .filter(Boolean) // 去掉无法映射的
}

const primaryGroups = computed(() => toGroups(props.primaryMuscles || []))
const secondaryGroups = computed(() => toGroups(props.secondaryMuscles || []))


</script>

<style scoped>
.muscle-diagram {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  border: 1px solid #e8e8e8;
  padding: 12px;
  margin-top: auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.diagram-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.diagram-title {
  font-size: 14px;
  font-weight: 700;
  color: #1a1a1a;
}

.diagram-body {
  display: flex;
  justify-content: center;
  padding: 4px 0;
  overflow: hidden;
}
</style>

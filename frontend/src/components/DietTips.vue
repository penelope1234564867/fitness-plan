<template>
  <a-card class="diet-card" :bordered="false">
    <template #title>
      <span class="diet-title">🥗 饮食建议</span>
    </template>

    <div v-if="diet">
      <!-- 热量和营养比例 -->
      <div class="nutrition-summary">
        <div class="nutrition-item">
          <div class="nutrition-value">{{ diet.daily_calories || '—' }}</div>
          <div class="nutrition-label">每日热量 (kcal)</div>
        </div>
        <div class="nutrition-item">
          <div class="nutrition-value">{{ diet.protein_ratio || '—' }}</div>
          <div class="nutrition-label">蛋白质</div>
        </div>
        <div class="nutrition-item">
          <div class="nutrition-value">{{ diet.carb_ratio || '—' }}</div>
          <div class="nutrition-label">碳水</div>
        </div>
        <div class="nutrition-item">
          <div class="nutrition-value">{{ diet.fat_ratio || '—' }}</div>
          <div class="nutrition-label">脂肪</div>
        </div>
      </div>

      <!-- 三餐推荐 -->
      <div v-if="diet.meals && Object.keys(diet.meals).length" class="meal-section">
        <a-divider style="margin: 12px 0" />
        <h4 class="section-subtitle">🍽️ 推荐餐单</h4>
        <a-row :gutter="12">
          <a-col
            v-for="(food, mealType) in diet.meals"
            :key="String(mealType)"
            :span="8"
          >
            <div class="meal-card">
              <div class="meal-type">{{ mealLabels[String(mealType)] || String(mealType) }}</div>
              <div class="meal-food">{{ food }}</div>
            </div>
          </a-col>
        </a-row>
      </div>

      <!-- 小贴士 -->
      <div v-if="diet.tips && diet.tips.length" class="tips-section">
        <a-divider style="margin: 12px 0" />
        <h4 class="section-subtitle">💡 饮食小贴士</h4>
        <ul class="tips-list">
          <li v-for="(tip, i) in diet.tips" :key="i">{{ tip }}</li>
        </ul>
      </div>
    </div>

    <div v-else>
      <a-empty description="暂无饮食建议" />
    </div>
  </a-card>
</template>

<script setup lang="ts">
import type { DietAdvice } from '@/types'

defineProps<{
  diet: DietAdvice | null | undefined
}>()

const mealLabels: Record<string, string> = {
  breakfast: '🌅 早餐',
  lunch: '☀️ 午餐',
  dinner: '🌙 晚餐',
  snack: '🍪 加餐',
}
</script>

<style scoped>
.diet-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.diet-title { font-size: 16px; font-weight: 600; }

.nutrition-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 8px;
}
.nutrition-item {
  text-align: center;
  padding: 12px 8px;
  background: linear-gradient(135deg, #fff7e6, #fff);
  border-radius: 10px;
  border: 1px solid #ffe7ba;
}
.nutrition-value {
  font-size: 22px;
  font-weight: 700;
  color: #d46b08;
}
.nutrition-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.section-subtitle {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.meal-card {
  padding: 12px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px solid #f0f0f0;
  margin-bottom: 8px;
  text-align: center;
}
.meal-type {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 4px;
}
.meal-food {
  font-size: 14px;
  color: #333;
}

.tips-list {
  padding-left: 20px;
  margin: 0;
}
.tips-list li {
  font-size: 13px;
  color: #555;
  line-height: 1.8;
}
</style>

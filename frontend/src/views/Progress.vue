<template>
  <div class="progress-container">
    <h2 class="page-title">📊 进度追踪</h2>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <a-spin size="large" />
      <p>加载数据中...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="records.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <h3>还没有训练数据</h3>
      <p>先去记录页添加训练记录，这里会展示你的进度图表</p>
      <a-button type="primary" @click="goToRecord" class="cta-button">
        📝 去记录训练
      </a-button>
    </div>

    <!-- 图表内容 -->
    <div v-else>
      <!-- 统计概览 -->
      <a-row :gutter="16" style="margin-bottom: 20px;">
        <a-col :span="6">
          <a-statistic title="总训练次数" :value="records.length" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="总组数" :value="totalSets" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="总次数" :value="totalReps" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="训练天数" :value="uniqueDays" suffix="天" />
        </a-col>
      </a-row>

      <!-- 训练重量趋势 -->
      <a-card class="chart-card" :bordered="false" v-if="weightData.length">
        <template #title>
          <span>⚡ 训练重量趋势</span>
        </template>
        <v-chart :option="weightChartOption" style="height: 300px" autoresize />
      </a-card>

      <!-- 难度分布 -->
      <a-card class="chart-card" :bordered="false" style="margin-top: 16px;">
        <template #title>
          <span>⭐ 难度分布</span>
        </template>
        <v-chart :option="difficultyChartOption" style="height: 300px" autoresize />
      </a-card>

      <!-- 训练频率（按日期） -->
      <a-card class="chart-card" :bordered="false" style="margin-top: 16px;">
        <template #title>
          <span>📅 训练频率</span>
        </template>
        <v-chart :option="frequencyChartOption" style="height: 300px" autoresize />
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart, BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { useRecordStore } from '@/stores/record'

// 注册 ECharts 组件
use([
  CanvasRenderer,
  LineChart,
  PieChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

const router = useRouter()
const recordStore = useRecordStore()
const records = computed(() => recordStore.records)
const loading = computed(() => recordStore.loading)

const totalSets = computed(() =>
  records.value.reduce((sum, r) => sum + (r.actual_sets || 0), 0),
)
const totalReps = computed(() =>
  records.value.reduce((sum, r) => sum + (r.actual_reps || 0), 0),
)
const uniqueDays = computed(() => {
  const days = new Set(records.value.map((r) => r.date))
  return days.size
})

// 训练重量趋势
const weightData = computed(() =>
  records.value.filter((r) => r.weight && r.weight > 0),
)
const weightChartOption = computed(() => ({
  tooltip: { trigger: 'axis' as const },
  grid: { left: 60, right: 20, bottom: 40, top: 20 },
  xAxis: {
    type: 'category' as const,
    data: weightData.value.map((r) => r.date),
    axisLabel: { rotate: 45, fontSize: 11 },
  },
  yAxis: { type: 'value' as const, name: '重量 (kg)' },
  series: [
    {
      data: weightData.value.map((r) => r.weight),
      type: 'line',
      smooth: true,
      lineStyle: { color: '#52c41a', width: 3 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(82, 196, 26, 0.3)' },
            { offset: 1, color: 'rgba(82, 196, 26, 0.05)' },
          ],
        },
      },
      itemStyle: { color: '#52c41a' },
    },
  ],
}))

// 难度分布（饼图）
const difficultyChartOption = computed(() => {
  const dist: Record<number, number> = {}
  records.value.forEach((r) => {
    dist[r.difficulty] = (dist[r.difficulty] || 0) + 1
  })
  const colors = ['#ff4d4f', '#ff7a45', '#faad14', '#52c41a', '#1890ff']
  return {
    tooltip: { trigger: 'item' as const },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '50%'],
        data: Object.entries(dist).map(([level, count]) => ({
          name: `${level} 星`,
          value: count,
        })),
        label: { show: true, formatter: '{b}: {c} 次' },
        itemStyle: {
          color: (params: any) => colors[params.dataIndex] || '#999',
        },
      },
    ],
  }
})

// 训练频率（按日期柱状图）
const frequencyChartOption = computed(() => {
  const freq: Record<string, number> = {}
  records.value.forEach((r) => {
    freq[r.date] = (freq[r.date] || 0) + 1
  })
  const sortedDates = Object.keys(freq).sort()
  return {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 40, right: 20, bottom: 40, top: 20 },
    xAxis: {
      type: 'category' as const,
      data: sortedDates,
      axisLabel: { rotate: 45, fontSize: 11 },
    },
    yAxis: { type: 'value' as const, name: '训练次数' },
    series: [
      {
        type: 'bar',
        data: sortedDates.map((d) => freq[d]),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: '#00b09b' },
              { offset: 1, color: '#96c93d' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  }
})

onMounted(() => {
  recordStore.fetchRecords()
})

function goToRecord() {
  router.push('/record')
}
</script>

<style scoped>
.progress-container {
  max-width: 1000px;
  margin: 0 auto;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}
.chart-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.loading-state {
  text-align: center;
  padding: 80px 20px;
}
.loading-state p {
  margin-top: 12px;
  color: #999;
}
.empty-state {
  text-align: center;
  padding: 80px 20px;
  animation: fadeInUp 0.5s ease-out;
}
.empty-icon {
  font-size: 80px;
  margin-bottom: 16px;
}
.empty-state h3 {
  font-size: 22px;
  color: #333;
  margin-bottom: 8px;
}
.empty-state p {
  color: #999;
  margin-bottom: 24px;
}
.cta-button {
  height: 48px;
  border-radius: 24px;
  font-size: 16px;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

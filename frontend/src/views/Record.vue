<template>
  <div class="record-container">
    <h2 class="page-title">📝 训练记录</h2>

    <!-- 记录表单 -->
    <RecordForm @saved="refreshRecords" />

    <!-- 历史记录 -->
    <a-card class="history-card" :bordered="false">
      <template #title>
        <span>📊 历史记录</span>
      </template>
      <template #extra>
        <a-button size="small" @click="refreshRecords" :loading="loading">
          🔄 刷新
        </a-button>
      </template>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <a-spin />
      </div>

      <!-- 空状态 -->
      <div v-else-if="records.length === 0" class="empty-state">
        <a-empty description="还没有训练记录">
          <template #image>
            <div style="font-size: 60px;">🏋️</div>
          </template>
        </a-empty>
      </div>

      <!-- 记录列表 -->
      <div v-else class="record-list">
        <a-list
          :data-source="records"
          :pagination="{
            pageSize: 10,
            showSizeChanger: false,
          }"
        >
          <template #renderItem="{ item }">
            <a-list-item class="record-item">
              <a-list-item-meta>
                <template #title>
                  <div class="record-title">
                    <strong>{{ item.exercise_name }}</strong>
                    <span class="record-date">{{ item.date }}</span>
                  </div>
                </template>
                <template #description>
                  <div class="record-detail">
                    <a-space wrap>
                      <a-tag v-if="item.target_muscle" color="blue">{{ item.target_muscle }}</a-tag>
                      <span>🏋️ 目标: {{ item.planned_sets }}×{{ item.planned_reps }}</span>
                      <span>✅ 实际: {{ item.actual_sets }}×{{ item.actual_reps }}</span>
                      <span v-if="item.weight">⚡ {{ item.weight }}kg</span>
                    </a-space>
                  </div>
                </template>
                <template #avatar>
                  <div class="difficulty-stars">
                    <a-rate :value="item.difficulty" :count="5" disabled size="small" />
                  </div>
                </template>
              </a-list-item-meta>
              <template #extra>
                <a-tag v-if="item.plan_id" color="orange">计划 #{{ item.plan_id }}</a-tag>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRecordStore } from '@/stores/record'
import RecordForm from '@/components/RecordForm.vue'

const route = useRoute()
const recordStore = useRecordStore()

const records = computed(() => recordStore.records)
const loading = computed(() => recordStore.loading)

// 从 URL 参数中读取 plan_id
const planId = computed(() => {
  const pid = route.query.plan_id
  return pid ? Number(pid) : undefined
})

onMounted(() => {
  refreshRecords()
})

function refreshRecords() {
  recordStore.fetchRecords(planId.value)
}
</script>

<style scoped>
.record-container {
  max-width: 900px;
  margin: 0 auto;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #333;
}
.history-card {
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.loading-state {
  text-align: center;
  padding: 40px;
}
.empty-state {
  padding: 40px;
}
.record-item {
  padding: 12px 0;
}
.record-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.record-date {
  font-size: 13px;
  color: #999;
  font-weight: normal;
}
.record-detail {
  margin-top: 4px;
}
.difficulty-stars {
  min-width: 80px;
}
</style>

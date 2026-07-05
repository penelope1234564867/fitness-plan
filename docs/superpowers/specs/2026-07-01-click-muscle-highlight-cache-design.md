# 点击动作高亮肌肉 + wger 懒加载缓存

## 问题

1. **点击动作行 → 即时高亮肌肉图**: 当前点动作只能打开 Drawer，Drawer 再去 wger 拉肌肉数据，高亮有延迟。需要点击动作行就直接在肌肉图上高亮对应的主动肌/辅助肌。

2. **wger 动作详情懒加载缓存**: 每次打开 Drawer 都调 `GET /api/wger/exercise/{id}`（虽然是本地缓存，但仍然重复）。需要只请求一次，之后从内存缓存读取。

## 方案

### 后端改动

#### 1. Exercise ORM 加 JSON 字段存肌肉数据

`backend/app/models/orm_models.py` — Exercise 表新增 `primary_muscles` 和 `secondary_muscles` JSON 列：

```python
primary_muscles = Column(Text, default="[]")    # JSON: [{"id": 4, "name_en": "Pectoral", "name_cn": "胸大肌"}]
secondary_muscles = Column(Text, default="[]")  # JSON 格式同上
```

#### 2. 缓存时写入肌肉数据

`backend/app/engine/exercise_cache.py` — `get_or_fetch_exercise()` 中，从 `get_exercise_detail()` 拿到 `primary_muscles` / `secondary_muscles` 后，JSON 序列化存入 Exercise 表。

#### 3. day-detail 接口返回肌肉数据

`backend/app/api/routes/fitness.py` — `_build_day_detail()` 中，构建 `exercise` 字典时附加 `primary_muscles` 和 `secondary_muscles`（从 Exercise 对象的 JSON 字段解析）。

### 前端改动

#### 1. TypeScript 类型

`frontend/src/types/index.ts` — `ExerciseInfo` 加字段：

```typescript
export interface ExerciseInfo {
  // ... 现有字段
  primary_muscles?: { id: number; name_en: string; name_cn: string }[]
  secondary_muscles?: { id: number; name_en: string; name_cn: string }[]
}
```

#### 2. workoutStore 肌肉操作方法

`frontend/src/stores/workout.ts` — 新增：
- `setActiveMuscles(slot: ExerciseSlot)`: 从 slot.exercise 读取肌肉数据，设置 activePrimaryMuscles / activeSecondaryMuscles
- `exerciseDetailCache: Map<number, {...}>`: wger 详情缓存
- `getCachedExerciseDetail(wgerId)`: 先查缓存，没有再调 API 并缓存
- `clearActiveMuscles()`: 清空肌肉高亮

#### 3. ExerciseRow 新增事件

`frontend/src/components/ExerciseRow.vue` — 点击动作信息区（`.exercise-info`）时，除了已有的 `show-detail`，新增 `highlight-muscles` 事件（由父组件决定是否响应）。

#### 4. DailyPlanPanel 连接

`frontend/src/components/DailyPlanPanel.vue` — 监听 ExerciseRow 的交互：
- 点击动作行 → 调用 `workoutStore.setActiveMuscles(slot)`
- Drawer 打开时：从 slot 读肌肉数据，不再重复调 wger API 拿肌肉
- Drawer 关闭时：不清空肌肉高亮（用户可能想对比）

#### 5. ExerciseDrawer 读缓存

`frontend/src/components/ExerciseDrawer.vue` — 打开时：
- 肌肉数据直接从 slot.exercise 读（已有，无需请求）
- 图片/描述等：调用 `workoutStore.getCachedExerciseDetail()` 读取/缓存
- 不再直接修改 `workoutStore.activePrimaryMuscles` / `activeSecondaryMuscles`

### 数据流

```
点击动作行
  → ExerciseRow emit('show-detail') + emit('highlight-muscles')
  → DailyPlanPanel 处理：
      1. openDrawer(slot) → 展开 Drawer
      2. workoutStore.setActiveMuscles(slot) → 从 slot.exercise.primary_muscles 读数据
      3. MuscleDiagram 响应 activePrimaryMuscles 变化 → 高亮肌肉图
      
打开 Drawer
  → 肌肉数据已从 slot.exercise 读取（无需请求）
  → 图片/描述：调 getCachedExerciseDetail()
    → 缓存命中：直接返回
    → 缓存未命中：调 API → 存入缓存 → 返回

关闭 Drawer
  → 不清空肌肉高亮（用户在肌肉图上看到的是当前选中的动作）
  → 如果高亮的是不同动作的数据，会被下一次 setActiveMuscles 覆盖
```

### 文件改动清单

| 文件 | 改动 |
|------|------|
| `backend/app/models/orm_models.py` | Exercise 表加 `primary_muscles`, `secondary_muscles` Text 列 |
| `backend/app/engine/exercise_cache.py` | `get_or_fetch_exercise()` 写入肌肉数据 |
| `backend/app/api/routes/fitness.py` | `_build_day_detail()` 返回 muscle 数据 |
| `frontend/src/types/index.ts` | ExerciseInfo 加 `primary_muscles` / `secondary_muscles` |
| `frontend/src/stores/workout.ts` | 加 `setActiveMuscles()`, `exerciseDetailCache`, `getCachedExerciseDetail()` |
| `frontend/src/components/ExerciseRow.vue` | 加 `highlight-muscles` emit |
| `frontend/src/components/DailyPlanPanel.vue` | 处理 muscle 高亮，更新 Drawer 数据源 |
| `frontend/src/components/ExerciseDrawer.vue` | 从 slot 读肌肉数据，用缓存获取详情 |

### 验证

1. 前端测试：`npm test` 检查所有已有测试仍通过
2. 后端测试：手动调用 `GET /api/fitness/day-detail?date=...` 检查 response 包含 `primary_muscles`
3. 手动测试：点击动作行 → 肌肉图即时高亮
4. 手动测试：连续打开/关闭 Drawer → 只请求一次 wger API

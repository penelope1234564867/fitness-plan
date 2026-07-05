# ProfilePage 改版设计 — v11 布局整合

## 概述

将 brainstorm session 中的 layout-v11 设计整合到项目的 ProfilePage，
包含：左侧个人信息/健身目标/训练状态三卡 + 统一保存 + 右侧周期路线图与科学训练知识轮播。

## 需求

1. 左侧面板：头像 + 标题行 → 个人信息卡 → 健身目标卡 → 训练状态卡 → 统一保存按钮
2. 右侧面板：周期路线图（现有 CycleRoadmapNew）+ 科学训练知识轮播卡（新增）
3. 前后端数据联动：一个接口保存所有字段

## 后端变更

### 新增接口：`PUT /api/user/profile-combined`

**Schema**（backend/app/models/schemas.py 新增）：

```python
class ProfileCombinedRequest(BaseModel):
    # 个人信息 → User 表
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    goal: Optional[str] = None

    # 训练状态 → UserCurrentState 表
    experience_level: Optional[str] = None
    workout_location: Optional[str] = None
    preferred_days: Optional[str] = None
```

**路由**（backend/app/api/routes/user.py 新增）：

```python
@router.put("/profile-combined")
async def update_profile_combined(data: schemas.ProfileCombinedRequest, db: Session = Depends(get_db)):
    # 1. 更新或创建 User 记录（身高/体重/年龄/性别/目标）
    # 2. 更新或创建 UserCurrentState 记录（经验/地点/训练日）
    # 3. 同一个事务提交
```

### Schema 变更

- `UserProfile` 保留不动（向后兼容）
- 新增 `ProfileCombinedRequest`

## 前端变更

### ProfilePage.vue — 完全重写

**布局结构**：

```
+----------------------------------+
|  profile-page (flex, gap: 24px)  |
|  +----------+  +--------------+  |
|  | left 340px|  | right flex:1 |  |
|  |          |  |             |  |
|  | [头像]   |  | 周期路线图    |  |
|  | [名字行]  |  | (CycleRoadmap |
|  |          |  |  New)        |  |
|  | 个人信息卡 |  |             |  |
|  | 健身目标卡 |  | 科学训练知识  |  |
|  | 训练状态卡 |  | (轮播卡)     |  |
|  |          |  |             |  |
|  | [保存全部] |  |             |  |
|  +----------+  +--------------+  |
+----------------------------------+
```

**左侧面板（从上到下）**：

1. **头像行** — 圆形渐变头像（♂/♀）+ 名字行 "180cm · 72kg" + 目标标签
2. **个人信息卡** ✏️ — 4 格 2×2：
   - 身高 (cm) | 体重 (kg)
   - 年龄 | 性别（♂/♀ 按钮）
   - 直接可编辑 input，无需切换编辑模式
3. **健身目标卡** 🎯 — 4 格 2×2 按钮：
   - 💪 增肌 / 🔥 减脂 / ✨ 塑形 / ❤️ 保持健康
   - 选中项高亮（橙底白字）
4. **训练状态卡** ⚙️ — 三行：
   - 经验：🌱 新手 / 💪 中级 / 🔥 高级（三选一按钮）
   - 地点：🏠 居家 / 🏋️ 健身房 / 🌳 户外（三选一按钮）
   - 训练日：7 个圆形日按钮（一二三四五六日），选中橙色填充
   - 下方显示 "每周 X 天"
5. **💾 保存全部设置** — 渐变橙色按钮，一次性保存所有数据

**右侧面板（从上到下）**：

1. **周期路线图** — 复用现有 CycleRoadmapNew 组件
2. **科学训练知识轮播卡** — 新增静态展示组件：
   - 标题行：📖 科学训练知识 + 1/2 页码 + 两个圆点指示器
   - 幻灯片容器（左右滑动切换）：
     - 第1页：PPL 三分化训练（推/拉/腿 三格说明）
     - 第2页：周期化训练（四个阶段 2×2 格说明）
   - 自动轮播：每 5 秒切换
   - 手动点击圆点可切换

### 数据流

1. `onMounted` → 分别请求 `GET /api/user/profile` 和 `GET /api/fitness/current-state` 填充表单
2. `cycleStore.fetchMacrocycles()` → 加载路线图数据
3. 点击「保存全部设置」→ `PUT /api/user/profile-combined` 一次性提交所有字段
4. 成功后重新 fetch profile + currentState 刷新显示

### 样式

- 追随 v11 的卡牌风格：圆角 16px、浅阴影、浅灰边框
- 橙色主题色（#f97316）贯穿选中态/按钮
- 响应式：768px 以下切换到纵向堆叠

## 数据库变更

无。所有字段已存在于 `User` 表和 `UserCurrentState` 表。

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| backend/app/models/schemas.py | 修改 | 新增 `ProfileCombinedRequest` |
| backend/app/api/routes/user.py | 修改 | 新增 `PUT /profile-combined` 路由 |
| frontend/src/views/ProfilePage.vue | 重写 | 按照 v11 布局重写 |
| frontend/src/services/api.ts | 修改 | 新增 `saveProfileCombined()` 方法 |
| frontend/src/types/index.ts | 修改 | 新增 TypeScript 类型 |

## 未涉及

- 引导页（OnboardingGuide / SetupWizard）不受影响
- 日历页（MainPage）不受影响
- CycleRoadmapNew 组件本身不改动

# Home 页面布局比例调整

**日期：** 2026-07-03
**状态：** 已批准 ✓

## 问题

Home 页面（MainPage.vue）左右栏比例失衡：
- 左栏固定 380px（26%），右栏无上限拉伸（72%+）
- 左栏内 CycleInfo + CalendarPanel 占固定高度，MuscleDiagram 被挤压
- 右栏日计划面板在宽屏下宽度超过 1000px，阅读体验差

## 修改方案

### 改动 1：MainPage.vue — Grid 弹性比例

```diff
- .main-content { display: flex; gap: 16px; ... }
- .left-column { width: 380px; flex-shrink: 0; ... }
+ .main-content {
+   display: grid;
+   grid-template-columns: clamp(320px, 36%, 480px) 1fr;
+   gap: clamp(16px, 2vw, 32px);
+   ...
+ }
+ .left-column { /* 去掉 width: 380px */ }
```

**效果比例：**
| 屏幕 | 容器 | 左栏 | 右栏 |
|------|------|------|------|
| 1920×1080 | 1440px | 480px (33%) | 928px |
| 1366×768 | 1270px | 457px (36%) | 781px |
| 1280×720 | 1184px | 426px (36%) | 726px |

### 改动 2：MuscleSection — 内部空间保障

```diff
- .muscle-section { flex: 1; ... }
+ .muscle-section { flex: 1.5; min-height: 140px; ... }
```

### 改动 3：DailyPlanPanel.vue — 右栏最大宽度

```diff
+ .daily-plan-panel { max-width: 800px; }
```

### 改动范围

3 个文件，约 15 行 CSS，无结构性重构。

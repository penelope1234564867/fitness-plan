# Dark Mode (日夜间模式) 设计文档

> 日期: 2026-07-04
> 状态: 待实现

## 概述

为 Fitness Plan 健身计划应用添加日夜间模式切换功能。通过 CSS 变量全面迁移 + Ant Design Vue ConfigProvider 实现完整的暗色主题支持。

## 技术方案

**方案 A：CSS 变量全面迁移 + Ant Design ConfigProvider**

- 所有硬编码颜色提取为 CSS 自定义属性
- Ant Design Vue v4 的 `theme.darkAlgorithm` 处理组件库暗色
- Pinia store 管理主题状态 + localStorage 持久化
- 跟随系统 `prefers-color-scheme` 偏好

## 颜色系统

### CSS 变量定义

全部变量在 `frontend/src/styles/theme.css` 中定义。

#### 背景色

| 变量名 | 亮色值 | 暗色值 |
|--------|--------|--------|
| `--bg-page` | `#f0f2f5` | `#141414` |
| `--bg-card` | `#ffffff` | `#1f1f1f` |
| `--bg-subtle` | `#f5f5f5` | `#2a2a2a` |
| `--bg-hover` | `#fafafa` | `#333333` |

#### 文字色

| 变量名 | 亮色值 | 暗色值 |
|--------|--------|--------|
| `--text-primary` | `#1a1a1a` | `#e5e5e5` |
| `--text-secondary` | `#555555` | `#a0a0a0` |
| `--text-muted` | `#999999` | `#666666` |
| `--text-inverse` | `#ffffff` | `#1a1a1a` |

#### 品牌/功能色

| 变量名 | 亮色值 | 暗色值（降低饱和度） |
|--------|--------|-------------------|
| `--brand-orange` | `#f97316` | `#d97706` |
| `--brand-orange-light` | `#fb923c` | `#b45309` |
| `--color-success` | `#22c55e` | `#16a34a` |
| `--color-error` | `#ef4444` | `#dc2626` |
| `--color-info` | `#3b82f6` | `#2563eb` |
| `--color-purple` | `#a855f7` | `#9333ea` |

#### 边框/阴影

| 变量名 | 亮色值 | 暗色值 |
|--------|--------|--------|
| `--border-color` | `#e8e8e8` | `#333333` |
| `--border-subtle` | `#f0f0f0` | `#2a2a2a` |
| `--shadow-card` | `0 2px 8px rgba(0,0,0,0.06)` | `0 2px 8px rgba(0,0,0,0.3)` |

#### 阶段色

| 变量名 | 亮色值 | 暗色值（提高亮度） |
|--------|--------|-------------------|
| `--phase-foundational` | `#3b82f6` | `#60a5fa` |
| `--phase-hypertrophy` | `#22c55e` | `#4ade80` |
| `--phase-strength` | `#f97316` | `#fb923c` |
| `--phase-deload` | `#a855f7` | `#c084fc` |

### 定义方式

```css
/* :root = 亮色模式 */
:root {
  --bg-page: #f0f2f5;
  --bg-card: #ffffff;
  /* ... */
}

/* .dark = 暗色模式 */
:root.dark {
  --bg-page: #141414;
  --bg-card: #1f1f1f;
  /* ... */
}
```

## 切换按钮

- **位置：** App.vue Header 右侧，头像按钮左侧
- **样式：** 圆形图标按钮，无背景色
- **图标：** 太阳 ☀️（亮色模式）/ 月亮 🌙（暗色模式）
- **动画：** 点击时图标旋转过渡

## 主题状态管理

### Pinia Store (`theme.ts`)

```typescript
interface ThemeState {
  mode: 'light' | 'dark';  // 当前主题模式
}
```

**逻辑流程：**
1. 初始化 → 读取 localStorage 的 `theme-mode`
2. 无存储 → 检测 `prefers-color-scheme: dark` 确定初始值
3. 切换按钮：`light ↔ dark` 直接翻转
4. 每次切换 → 写入 localStorage + 更新 `<html>` 的 `.dark` class
5. 监听 `matchMedia('prefers-color-scheme')` 变化 → 同步更新（仅当用户无手动选择时）
6. **注意：** 首次访问跟随系统，但手动切换后以手动为准，不再自动跟随系统

## Ant Design 暗色主题

在 `App.vue` 中用 `<a-config-provider>` 包裹整个应用：

```vue
<a-config-provider :theme="antTheme">
  <router-view />
</a-config-provider>
```

- `resolved === 'dark'` → `theme.darkAlgorithm`
- `resolved === 'light'` → `theme.defaultAlgorithm`

## 迁移范围

共约 20 个文件需要替换硬编码颜色为 CSS 变量：

| 文件 | 改动内容 |
|------|---------|
| 新建: `src/styles/theme.css` | 定义所有 CSS 变量 |
| 新建: `src/stores/theme.ts` | 主题状态管理 |
| 修改: `src/main.ts` | 引入 theme.css |
| 修改: `src/App.vue` | 加 ConfigProvider + 切换按钮 + .dark class |
| 修改: 所有 view 和 component 文件 | `#fff` → `var(--bg-card)` 等替换 |

组件级别替换是机械操作：查找颜色值 → 替换为对应 CSS 变量。

## 实现顺序

1. 创建 `theme.css` 定义 CSS 变量
2. 创建 `theme.ts` 主题 store
3. 修改 `main.ts` 引入 theme.css
4. 修改 `App.vue`：加 ConfigProvider + 切换按钮 + 暗色 class 控制
5. 逐个组件替换颜色（从高频使用的开始）
6. 全局验证亮色/暗色效果

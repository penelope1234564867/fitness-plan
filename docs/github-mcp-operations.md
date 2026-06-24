# Fitness Plan GitHub 操作说明书

> 本项目 `fitness-plan` 的 GitHub 操作指南。
>
> 仓库地址：https://github.com/penelope1234564867/fitness-plan

---

## 一、仓库结构

```
fitness-plan/
├── backend/                           # FastAPI 后端
│   ├── app/
│   │   ├── agents/                    # AI Agent 实现
│   │   ├── api/                       # API 路由
│   │   ├── services/                  # 服务层编排
│   │   ├── models/                    # 数据模型
│   │   ├── mcp_servers/               # MCP Server
│   │   ├── config.py
│   │   └── database.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env
├── frontend/                          # Vue3 前端
│   ├── src/
│   │   ├── components/                # 组件
│   │   ├── views/                     # 页面
│   │   ├── stores/                    # 状态管理
│   │   ├── services/                  # API 调用
│   │   └── types/                     # 类型定义
│   └── package.json
├── docs/                              # 项目文档
│   ├── plan.md                        # 开发计划
│   ├── design.md                      # 架构设计
│   ├── wger-mcp.md                    # Wger 集成文档
│   ├── wger-mcp-implementation.md     # MCP 实现细节
│   └── github-mcp-operations.md       # 本文件
├── README.md
└── .gitignore
```

---

## 二、日常操作流程

### 2.1 查看当前状态

```bash
git status                # 查看有哪些文件改动了
git log --oneline -5      # 查看最近 5 条提交记录
```

### 2.2 提交代码到 GitHub

每完成一个功能或修改，执行以下三步：

```bash
# 第 1 步：添加文件到暂存区
git add <文件名>           # 添加单个文件
git add backend/           # 添加整个目录
git add .                  # 添加所有改动

# 第 2 步：提交（写清楚改了什么）
git commit -m "类型: 描述"

# 第 3 步：推送到 GitHub
git push origin main
```

**提交信息的格式：**

| 类型 | 什么时候用 |
|------|-----------|
| `feat:` | 添加新功能 |
| `fix:` | 修 Bug |
| `docs:` | 改文档 |
| `refactor:` | 重构代码 |
| `style:` | 改格式（不影响逻辑） |

示例：
```bash
git commit -m "feat: 实现 ExerciseAgent 搜索训练动作"
git commit -m "docs: README 改为中文"
git commit -m "fix: 修复天气查询接口报错"
```

### 2.3 拉取最新代码

```bash
git pull origin main
```

每次开始工作前先拉取，确保你的本地代码是最新的。

---

## 三、在 Claude Code 中操作

直接在对话里说就可以，不需要记命令：

| 你想做什么 | 怎么说 |
|-----------|--------|
| 查看状态 | "看看现在 git 状态" |
| 提交文件 | "帮我 add README.md 然后 commit 推送" |
| 批量提交 | "把我改的东西都提交推送" |
| 创建 Issue | "帮我建个 Issue，标题是 XXX" |
| 查看分支 | "现在在哪个分支？" |

Claude Code 会先弹窗让你确认，确认后才执行。

---

## 四、GitHub 项目设置

### 4.1 必须保护的配置

| 文件 | 原因 | 处理方式 |
|------|------|---------|
| `.env` (后端) | 含 API Key，不能上传 | `.gitignore` 已排除 |
| `.env` (前端) | 含 API 地址配置 | `.gitignore` 已排除 |
| `node_modules/` | 几百 MB，GitHub 拒绝 | `.gitignore` 已排除 |
| `__pycache__/` | Python 缓存文件 | `.gitignore` 已排除 |

### 4.2 仓库可见性

- 仓库：**公开（public）**
- 任何人都可以查看和 clone
- 只有你可以 push

---

## 五、常见命令速查

```bash
git status                     # 查看工作区状态
git add <文件>                  # 添加文件到暂存区
git commit -m "消息"            # 提交改动
git push origin main           # 推送到 GitHub
git pull origin main           # 拉取 GitHub 最新代码
git log --oneline              # 查看提交历史
git diff                       # 查看具体改了什么
```

> 你只需要记住 `git add → git commit → git push` 三步就够了，其他命令用的时候让 Claude Code 帮你就行。

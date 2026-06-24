# GitHub MCP 操作指南

> 如何通过 **GitHub MCP**（Model Context Protocol）工具直接在 Claude Code 中管理健身计划仓库。

---

## 目录

1. [什么是 GitHub MCP？](#一什么是-github-mcp)
2. [可用工具清单](#二可用工具清单)
3. [日常操作示例](#三日常操作示例)
4. [Git 操作工作流](#四-git-操作工作流)
5. [Issue / PR 管理](#五-issue--pr-管理)
6. [常见场景](#六常见场景)

---

## 一、什么是 GitHub MCP？

**GitHub MCP** 是 Claude Code 内置的 MCP 服务器，它提供了一套 GitHub API 的封装工具，让你可以直接通过自然语言对话来操作 GitHub 仓库，而不需要手动输入 git 命令。

### 原理

```
你发指令 → Claude Code → GitHub MCP 工具 → GitHub API → 仓库变更
```

### 优势

- ✅ **不用记 git 命令** — 说人话就能操作
- ✅ **操作可追溯** — 每一步都有详细日志
- ✅ **权限可控** — Claude Code 会弹窗让你确认每次操作
- ✅ **批量操作** — 一次可以 add / commit / push 多个文件

---

## 二、可用工具清单

以下是 GitHub MCP 提供的主要工具：

### 2.1 文件操作

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `create_or_update_file` | 创建或更新单个文件 | 写新文档、修改现有代码 |
| `push_files` | 批量推送多个文件（一次 commit） | 同时新增/修改多个文件后提交 |

### 2.2 仓库管理

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `create_repository` | 创建新仓库 | 新建项目 |
| `fork_repository` | Fork 别人的仓库 | 参与开源 |
| `search_repositories` | 搜索仓库 | 找自己的或别人的仓库 |

### 2.3 分支管理

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `create_branch` | 创建新分支 | 开发新功能前建分支 |
| `get_file_contents` | 获取文件内容 | 查看某个分支上的文件 |

### 2.4 Issue 管理

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `create_issue` | 创建 Issue | 记录 bug 或需求 |
| `list_issues` | 列出 Issue | 查看待办事项 |
| `get_issue` | 查看 Issue 详情 | 了解某个问题讨论 |
| `update_issue` | 更新 Issue | 修改状态、添加标签 |
| `add_issue_comment` | 添加评论 | 回复讨论 |
| `search_issues` | 搜索 Issue/PR | 全局搜索 |

### 2.5 Pull Request 管理

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `create_pull_request` | 创建 PR | 提交代码审查 |
| `get_pull_request` | 查看 PR 详情 | 了解 PR 内容 |
| `list_pull_requests` | 列出 PR | 查看所有打开的 PR |
| `merge_pull_request` | 合并 PR | 审查通过后合并 |
| `get_pull_request_files` | 查看 PR 修改的文件 | Code Review |
| `get_pull_request_comments` | 查看 PR 评论 | 查看审查意见 |
| `create_pull_request_review` | 提交 PR 审查意见 | Code Review |
| `update_pull_request_branch` | 更新 PR 分支 | 同步最新代码 |

### 2.6 搜索

| 工具 | 功能 | 典型场景 |
|------|------|---------|
| `search_code` | 搜索代码 | 在 GitHub 上全局搜代码 |
| `search_issues` | 搜索 Issue/PR | 查找相关问题 |
| `search_users` | 搜索用户 | 找人 |
| `search_repositories` | 搜索仓库 | 找项目 |

---

## 三、日常操作示例

### 3.1 查看当前仓库状态

```bash
# 在终端中执行
git status
git log --oneline
```

### 3.2 创建文件并提交

**场景**：新建一个文档并推送到 GitHub。

直接在对话中说：

> "在 docs/ 下新建一个文件 `xxx.md`，内容是 ...，然后帮我 add 和 push"

Claude Code 会依次：
1. 用 `Write` 工具创建文件
2. 用 `Bash` 执行 `git add` / `git commit` / `git push`

### 3.3 修改文件并提交

**场景**：修改 README 后推送。

> "把 README.md 的某部分改成这样，然后提交推送"

Claude Code 会：
1. 用 `Edit` 工具修改文件
2. 用 `Bash` 执行 git 命令提交

### 3.4 创建新分支

```bash
# 终端执行
git checkout -b feature/new-feature
git push origin feature/new-feature
```

或在对话中说：

> "创建一个新分支 `feature/xxx` 并切换到它"

---

## 四、Git 操作工作流

### 4.1 标准提交流程

```
你: "帮我写一个 xxx 文件，然后加进去"
     ↓
Claude Code 创建 / 修改文件
     ↓
你确认修改内容
     ↓
Claude Code 执行 git add / commit / push
     ↓
完成 ✅
```

### 4.2 完整示例：提交这份文档

```bash
# 第1步：查看状态
git status
# 输出：有未跟踪的文件 docs/github-mcp-operations.md

# 第2步：添加到暂存区
git add docs/github-mcp-operations.md

# 第3步：提交
git commit -m "docs: 添加 GitHub MCP 操作指南"

# 第4步：推送到 GitHub
git push origin main
```

### 4.3 多文件提交

```bash
# 添加所有文档变更
git add docs/

# 提交
git commit -m "docs: 更新项目文档"

# 推送
git push origin main
```

### 4.4 查看提交历史

```bash
# 查看最近5条
git log --oneline -5

# 查看某次提交的改动
git show <commit-hash>
```

---

## 五、Issue / PR 管理

### 5.1 创建 Issue

在对话中直接说：

> "创建一个 Issue，标题是'添加训练记录图表功能'，内容描述一下需求"

Claude Code 会调用 `create_issue` 工具，在你仓库中创建 Issue。

### 5.2 查看 Issue 列表

> "看看仓库里有哪些打开的 Issue"

调用 `list_issues` 工具返回列表。

### 5.3 创建 Pull Request

在开发完一个功能后：

> "把我当前分支的修改提交，然后创建一个 PR 到 main 分支"

Claude Code 会：
1. git add / commit / push
2. 调用 `create_pull_request` 创建 PR

### 5.4 审查 PR

> "看看 PR #1 改了哪些文件"

调用 `get_pull_request_files` 查看变更文件列表，然后审查代码。

---

## 六、常见场景

### 场景 1：写完文档 → 提交推送

```mermaid
graph LR
    A[写文件] --> B[git add]
    B --> C[git commit]
    C --> D[git push]
    D --> E[完成]
```

### 场景 2：修 Bug → 开 PR

```mermaid
graph LR
    A[创建分支] --> B[修改代码]
    B --> C[提交推送]
    C --> D[创建 PR]
    D --> E[请求 Review]
```

### 场景 3：日常同步

```bash
# 拉取最新代码
git pull origin main

# 查看自己有没有未提交的
git status

# 有改动就提交
git add .
git commit -m "描述改动"
git push origin main
```

### 常用 git 命令速查

| 命令 | 作用 | 何时用 |
|------|------|--------|
| `git status` | 查看工作区状态 | 每次操作前 |
| `git add <file>` | 添加文件到暂存区 | 准备提交时 |
| `git add .` | 添加所有改动 | 批量提交时 |
| `git commit -m "msg"` | 提交 | 确认改动后 |
| `git push origin main` | 推送到远程 | 提交后 |
| `git pull origin main` | 拉取远程更新 | 开始工作前 |
| `git log --oneline` | 查看提交历史 | 查看记录时 |
| `git checkout -b <name>` | 创建并切换分支 | 开发新功能时 |

---

> **提示**：所有 Git 操作在 Claude Code 中都会经过你的确认弹窗，不用担心误操作。放心试！

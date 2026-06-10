---
name: "superpowers"
description: "Provides TDD, systematic debugging, brainstorming, planning, and code review workflow for coding agents. Invoke when starting any new feature, debugging complex issues, or doing code review."
---

# Superpowers - AI编程代理的开发方法论

> 来源: https://github.com/obra/superpowers (MIT License, by Jesse Vincent & Prime Radiant)

**核心思想**: 在Coding Agent写代码前，先"退一步"问清楚用户真正想做什么，并提供完整的可组合skills工作流，确保代码质量和工程纪律。

## 基础工作流 (The Basic Workflow)

任何一个新功能开发都要经过7个阶段：

### 1. brainstorming (头脑风暴)
- **触发时机**: 写代码前
- **做什么**: 用苏格拉底式提问细化想法，探索替代方案
- **产出**: 设计文档，分小段呈现给用户确认

### 2. using-git-worktrees (Git分支隔离)
- **触发时机**: 设计获批后
- **做什么**: 在新分支创建隔离工作区，运行项目设置，验证测试基线

### 3. writing-plans (编写计划)
- **触发时机**: 设计获批
- **做什么**: 把工作拆分成2-5分钟的小任务
- **要求**: 每个任务有精确的文件路径、完整代码、验证步骤

### 4. subagent-driven-development / executing-plans (子代理驱动开发)
- **触发时机**: 计划获批
- **做什么**: 为每个任务分配新的子代理，两阶段审查
  - 第一阶段: 规范合规性
  - 第二阶段: 代码质量
- 或者: 批量执行+人工检查点

### 5. test-driven-development (测试驱动开发 - TDD)
- **触发时机**: 实现过程中
- **RED-GREEN-REFACTOR循环**:
  1. 写一个失败的测试
  2. 看它失败（确认是真正的失败）
  3. 写最小代码让测试通过
  4. 看它通过
  5. 提交
- **铁律**: 测试前写的代码要删掉

### 6. requesting-code-review (代码审查请求)
- **触发时机**: 任务之间
- **做什么**: 对照计划审查，按严重程度报告问题
- **关键问题**: 阻塞进度

### 7. finishing-a-development-branch (完成开发分支)
- **触发时机**: 任务完成
- **做什么**: 验证测试，提供选项 (merge/PR/keep/discard)，清理worktree

## 内置Skills库 (按类别)

### 🧪 Testing (测试)
- **test-driven-development** - RED-GREEN-REFACTOR循环 (含反模式参考)

### 🐛 Debugging (调试)
- **systematic-debugging** - 4阶段根因排查 (含root-cause-tracing, defense-in-depth, condition-based-waiting)
- **verification-before-completion** - 确保真正修好了

### 🤝 Collaboration (协作)
- **brainstorming** - 苏格拉底式设计优化
- **writing-plans** - 详细实施计划
- **executing-plans** - 批量执行+检查点
- **dispatching-parallel-agents** - 并发子代理工作流
- **requesting-code-review** - 审查前自检
- **receiving-code-review** - 响应反馈
- **using-git-worktrees** - 并行开发分支
- **finishing-a-development-branch** - merge/PR决策
- **subagent-driven-development** - 两阶段审查的快速迭代

### 📚 Meta (元)
- **writing-skills** - 创建新skill的最佳实践
- **using-superpowers** - skills系统入门

## 核心哲学 (Philosophy)

1. **Test-Driven Development** - 永远先写测试
2. **Systematic over ad-hoc** - 流程胜于猜测
3. **Complexity reduction** - 简单是首要目标
4. **Evidence over claims** - 先验证再宣告成功

## 触发时机表

| 场景 | 调用的skill |
|------|------------|
| 用户提出新需求/新想法 | `brainstorming` |
| 收到"开始实现"指令 | `using-git-worktrees` + `writing-plans` |
| 计划获批 | `subagent-driven-development` / `executing-plans` |
| 实现具体功能 | `test-driven-development` (强约束TDD) |
| 任务卡住/遇到bug | `systematic-debugging` |
| 完成一组任务 | `requesting-code-review` |
| 修复完成 | `verification-before-completion` |
| 整个feature完成 | `finishing-a-development-branch` |

## 与Trae IDE工具协同

- **TodoWrite**: 实现`writing-plans` (拆任务、优先级排序)
- **Task (subagent_type)**: 实现`subagent-driven-development` (分发独立任务)
- **WebSearch/WebFetch**: 实现`brainstorming` (查文档找替代方案)
- **TRAE-code-review skill**: 实现`requesting-code-review`
- **TRAE-debugger skill**: 实现`systematic-debugging`
- **AskUserQuestion**: 实现`brainstorming` (苏格拉底式提问)
- **Skill (skill-creator)**: 实现`writing-skills` (创建新skill)
- **Bash/Edit/Read**: 实现`using-git-worktrees` (分支操作)

## 使用承诺

调用本skill后，AI Agent应**强制**遵循：
- ✅ 任何功能开发都先 brainstorming
- ✅ 任何代码都先写测试 (TDD)
- ✅ 任何修复都先 systematic-debugging
- ✅ 任何完成都先 verification-before-completion
- ✅ 任何计划都按 2-5分钟小任务拆分
- ✅ 任何代码完成都发起 code-review

**这是"必须"工作流，不是"建议"工作流！**

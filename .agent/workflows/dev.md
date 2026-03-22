---
description: 统一主工作流 - 一个命令覆盖所有开发场景。使用 /dev 启动。
---

# Dev - 统一主工作流

一个命令，覆盖从需求分析到部署的完整开发流程，以及日常维护操作。

## 命令一览

```
/dev                         # 显示命令列表
/dev start                   # 启动/继续完整开发流程
/dev start auto              # 自动模式（检查通过后自动继续）
/dev start status            # 查看开发进度
/dev start goto <phase_key>  # 跳转到指定阶段
/dev start skip              # 跳过当前阶段
/dev start reset             # 重置状态

/dev plan                    # 编码前创建实现计划（等待确认）
/dev fix                     # 修复构建错误 + 清理死代码
/dev test                    # 测试（TDD + E2E）
/dev review                  # 代码审查
/dev git                     # Git 操作（提交、分支、PR）
/dev skill                   # Skill 管理
```

---

## 🌍 全局规则（所有命令生效）

### Windows PowerShell 规范

- **Python 命令必须加 `uv run` 前缀**，禁止直接 `python`
- **禁止 `cd` 命令**，使用 `cwd` 参数
- **使用 PowerShell 语法**：`dir`/`Get-ChildItem`（不是 `ls`）、`Remove-Item`（不是 `rm`）
- **命令链接用 `;`**，禁止 `&&` 或 `||`

| 操作        | ✅ 用                     | ❌ 禁止            |
| ----------- | ------------------------- | ------------------ |
| 安装包      | `uv add package`          | `pip install`      |
| 运行 Python | `uv run python script.py` | `python script.py` |
| 列文件      | `dir` / `Get-ChildItem`   | `ls`               |
| 删除        | `Remove-Item`             | `rm`               |
| 切目录      | `cwd` 参数                | `cd`               |
| 链接命令    | `;`                       | `&&`               |

### 教科书溯源（Textbook-Sourced Coding）

**所有生成的代码必须有教科书来源。** 这是本项目的核心原则。

1. **加载映射**: 读取 `.agent/config/textbook-skill-mapping.yaml`，找到当前 skill 对应的教科书
2. **查阅来源**: 通过 `textbooks/topic_index.json` 定位相关章节，然后读取 `data/mineru_output/{book_key}/{book_key}/auto/{book_key}.md` 中的具体内容
3. **引用标注**: 在生成的代码中用注释标明来源:
   ```python
   # Ref: Goodfellow et al., Deep Learning, Ch8.5 — Adam optimizer update rule
   # Ref: Ramalho, Fluent Python, Ch17 — Generator-based pipeline pattern
   ```
4. **无来源不生成**: 如果教科书中找不到相关内容，明确告知用户并说明原因

| Skill                      | Primary Textbooks                                           |
| -------------------------- | ----------------------------------------------------------- |
| `dev-senior_backend`       | Fluent Python, Python Cookbook, Cosmic Python, Art of PG    |
| `dev-senior_frontend`      | JS Definitive Guide, Eloquent JS, TS Deep Dive, YDKJS ×6    |
| `dev-senior_architect`     | CLRS, Manning IR, DDIA, Clean Architecture                  |
| `dev-senior_data_engineer` | Fluent Python, Python Cookbook, DDIA, Art of PostgreSQL     |
| `dev-senior_qa`            | pytest Book, Google SWE, Python Cookbook, Fluent Python     |
| `dev-senior_devops`        | Pro Git, SRE, Release It!                                   |
| `dev-code_reviewer`        | Clean Code, Refactoring, Fluent Python, JS Definitive Guide |
| `dev-product_manager`      | Don't Make Me Think, Design of Everyday Things              |

完整映射见: `.agent/config/textbook-skill-mapping.yaml`

### 代码质量底线

- 函数 ≤ 50 行，文件 ≤ 800 行，嵌套 ≤ 4 层
- 不可变模式优先（创建新对象，不修改原对象）
- 无 magic number，无 console.log，无硬编码密钥
- 使用环境变量管理密钥
- 参数化查询防 SQL 注入，textContent 防 XSS

---

## 📦 `/dev start` - 完整开发流程

一个命令，完成从需求分析到部署的完整开发流程。借鉴 MetaGPT 多角色协作模式。自动跳过已完成的阶段。

// turbo-all

### 执行步骤

**Step 0: Session Review Gate（每次 `/dev` 启动时强制执行）**

每次调用 `/dev` 时，必须**重新严格审查**所有已完成阶段，确认文档内容与 Review 结论一致：

1. 读取 `.dev-state.yaml`，列出所有 `status: completed` 的阶段
2. 对每个已完成阶段，**重新读取产出物原文**，逐项验证：
   - 产出物内容是否与 Review 文件中记录的修复一致
   - 是否有新的内容问题（章节编号错误、数据矛盾、结构问题等）
   - 上次 Review 标记的 MEDIUM 问题处理计划是否仍然合理
3. 如发现新问题：
   - HIGH/CRITICAL → 必须先修复，追加 Re-Review 到 Review 文件
   - MEDIUM → 记录，询问用户是否阻塞当前阶段
4. 输出 Session Review 摘要表（含每阶段结论）
5. 全部 🟢 → 继续当前阶段

> **这不是走过场的状态检查。** 必须实际打开文档、阅读内容、核对一致性。每次 `/dev` 都是一次完整的质量门禁。

**Step 1-8: 正常执行流程**

1. 读取 `.dev-state.yaml` 获取当前状态
   - 不存在则从 `requirements` 阶段开始
   - 已完成的阶段自动跳过
   - `in_progress` 的阶段继续执行
2. 查找对应 step 文件 → `.agent/workflows/full-development-steps/`
3. 加载角色 → `.agent/workflows/metagpt-enhanced/roles.yaml`
4. **Template-First**: 先找 `.agent/templates/` 和 `.agent/scripts/` 中的现成资源
5. 执行任务
6. **⚠️ 阶段 Review（强制）** — 每个阶段完成后必须执行 Phase Review Protocol
7. **🔴 如有 HIGH/CRITICAL** → 作者修复 → **Re-Review 验证修复（强制，追加到同一 Review 文件）** → 通过后才能继续
8. Review 通过后更新 `.dev-state.yaml`，询问是否继续下一阶段

> **铁律: 改了就要 Re-Review。** 任何阶段产出物被修改后（无论是因为 Review 修复还是其他原因），Reviewer 必须重新验证修改内容并更新 Review 文件。未经 Re-Review 不可标记完成。

### ⚠️ Phase Review Protocol（每阶段完成后强制执行）

**每个阶段完成后，必须加载 `dev-phase_reviewer` skill 执行 Review，通过后才能标记完成并进入下一阶段。**

**🔴 核心规则: 不可自审 — Reviewer 必须是与作者不同的角色。**

执行步骤：

1. 加载 skill: `.agent/skills/dev-phase_reviewer/SKILL.md`
2. **确定 Reviewer** — 按下方 Reviewer 分配表，Reviewer 不可与作者为同一角色
3. 根据阶段类型自动加载对应的 review 清单（skill 内部分发）
4. **严格审查** — Reviewer 必须独立、严格审查，不迁就作者。发现问题必须如实记录
5. 生成 Review 报告 → 保存到 `docs/reviews/phase-{NN}-{phase_key}.md`
6. 🔴 CRITICAL/HIGH → 作者修复后 Reviewer 重新验证（Re-Review 追加到同一文件）
7. 🟡 MEDIUM → 记录处理计划（哪个阶段解决），用户确认后可继续
8. 🟢 全部通过 → 标记阶段完成

Reviewer 分配表（不可自审）：

| 阶段           | 作者             | Reviewer            | 分配理由                         |
| -------------- | ---------------- | ------------------- | -------------------------------- |
| `requirements` | Alice (PM)       | Bob (Architect)     | 架构师验证需求的可行性和完整性   |
| `prd`          | Alice (PM)       | Bob (Architect)     | 架构师验证用户故事的技术可实现性 |
| `architecture` | Bob (Architect)  | Charlie (Tech Lead) | 技术主管验证架构的可任务分解性   |
| `stories`      | Charlie (Lead)   | Bob (Architect)     | 架构师验证任务与架构的一致性     |
| `database`     | Bob (Architect)  | David (Backend)     | 后端工程师验证数据模型的可用性   |
| `backend`      | David (Backend)  | Grace (Reviewer)    | 代码审查专家审查代码质量         |
| `frontend`     | Eve (Frontend)   | Grace (Reviewer)    | 代码审查专家审查代码质量         |
| `review`       | Grace (Reviewer) | Charlie (Tech Lead) | 技术主管最终确认                 |
| `deployment`   | Henry (DevOps)   | Bob (Architect)     | 架构师验证部署与架构的一致性     |

Review 类型映射：

| 阶段                                                          | Review 类型 | 清单文件                          | Review 产出物                            |
| ------------------------------------------------------------- | ----------- | --------------------------------- | ---------------------------------------- |
| requirements, prd, architecture, stories, database            | 文档类      | `references/document-review.md`   | `docs/reviews/phase-{NN}-{phase_key}.md` |
| backend, frontend, review                                     | 代码类      | `references/code-review.md`       | `docs/reviews/phase-{NN}-{phase_key}.md` |
| deployment                                                    | 部署类      | `references/deployment-review.md` | `docs/reviews/phase-{NN}-{phase_key}.md` |

Review 文件命名规则: `phase-{序号:02d}-{phase_key}.md`，例如 `phase-04-architecture.md`

### 阶段表

| 顺序 | Phase Key      | 名称       | 角色             | Step 文件                 | Review 类型 |
| ---- | -------------- | ---------- | ---------------- | ------------------------- | ----------- |
| 1    | `requirements` | 需求分析   | Alice (PM)       | `step-01-requirements.md` | 文档类      |
| 2    | `prd`          | PRD        | Alice (PM)       | `step-02-prd.md`          | 文档类      |
| 3    | `architecture` | 系统架构   | Bob (Architect)  | `step-03-architecture.md` | 文档类      |
| 4    | `stories`      | 任务分解   | Charlie (Lead)   | `step-04-stories.md`      | 文档类      |
| 5    | `database`     | 数据库设计 | Bob (Architect)  | `step-05-database.md`     | 文档类      |
| 6    | `backend`      | 后端开发   | David (Backend)  | `step-06-backend.md`      | 代码类      |
| 7    | `frontend`     | 前端开发   | Eve (Frontend)   | `step-07-frontend.md`     | 代码类      |
| 8    | `review`       | 代码审查   | Grace (Reviewer) | `step-08-review.md`       | 代码类      |
| 9    | `deployment`   | 部署       | Henry (DevOps)   | `step-09-deployment.md`   | 部署阶段    |

**Phase key 顺序**: `requirements` → `prd` → `architecture` → `stories` → `database` → `backend` → `frontend` → `review` → `deployment`

### Template-First 资源映射

| Phase Key    | 模板 (`.agent/templates/`) | 脚本 (`.agent/scripts/`)                            |
| ------------ | -------------------------- | --------------------------------------------------- |
| `stories`    | `docs/plan.md.template`    | -                                                   |
| `backend`    | `backend/*.template`       | `scaffold.py feature --name <name> --type backend`  |
| `frontend`   | `frontend/*.template`      | `scaffold.py feature --name <name> --type frontend` |
| `review`     | -                          | `env_check.py --files`                              |
| `deployment` | `.vscode/tasks.json`       | `env_check.py --env production`                     |

### 自动验收检查（Phase Review 的第一步）

| Phase        | 自动检查命令                                                                              |
| ------------ | ----------------------------------------------------------------------------------------- |
| Requirements | 文件存在 + 非空: `docs/requirements/requirements.md`                                      |
| PRD          | 文件存在 + 非空: `docs/requirements/prd.md`                                               |
| Architecture | 文件存在 + 非空: `docs/architecture/system-architecture.md`                               |
| Stories      | 文件存在 + 非空: `docs/sprints/sprint-plan.md`                                            |
| Database     | 文件存在: `docs/codemaps/database.md`                                                     |
| Backend      | `uv run ruff check engine/ backend/`, `cd payload && npm run build`                       |
| Frontend     | `cd payload && npx tsc --noEmit`, `cd payload && npm run lint`                            |
| Review       | No CRITICAL issues in review report                                                       |
| Deployment   | Engine `/engine/health` 返回 ok，Payload Admin 可登录，`docs/v2.0/deployment.md` 已生成   |

### 状态管理

- `status`: 读取 `.dev-state.yaml`，显示每阶段状态
- `reset`: 删除 `.dev-state.yaml`
- `skip`: 标记当前阶段 `skipped`，进入下一阶段
- `goto <phase_key>`: 跳转到指定阶段

### 配置选项 (`.dev-state.yaml`)

```yaml
config:
  parallel_frontend_backend: true # 前后端并行
  auto_check: true # 自动验收
  docs_dir: docs # 文档目录
```

### 项目路径参考

| 资源            | 路径                                       |
| --------------- | ------------------------------------------ |
| 需求分析文档    | `docs/requirements/requirements.md`        |
| PRD 文档        | `docs/requirements/prd.md`                 |
| 架构文档        | `docs/architecture/system-architecture.md` |
| Sprint 计划     | `docs/sprints/sprint-plan.md`              |
| US 计划         | `docs/plans/US-xxx-plan.md`                |
| **阶段 Review** | `docs/reviews/phase-{NN}-{phase_key}.md`   |
| 后端代码        | `backend/app/`                             |
| 前端代码        | `frontend/src/`                            |
| 数据库 CodeMap  | `docs/codemaps/database.md`                |

---

## 📝 `/dev plan` - 实现计划

在写代码之前创建完整的实现计划。**必须等待用户确认后才能开始编码。**

### 何时使用

- 新功能开发、重大架构变更、复杂重构、需求不明确

### 流程

1. **需求重述** - 用清晰术语重新表述，列出假设和约束
2. **分解为阶段** - 具体可操作步骤，识别依赖和风险
3. **评估复杂度** - High/Medium/Low + 时间估算
4. **⚠️ 等待确认** - 用户明确确认前不写任何代码

### 计划模板

```markdown
# 实现计划: [功能名称]

## 概述

[2-3 句话概述]

## 实现阶段

### 阶段 1: [名称]

1. **[步骤]** (文件: path/to/file)
   - 操作 / 原因 / 依赖 / 风险

## 测试策略

- 单元/集成/E2E

## 风险与缓解

## 估算复杂度: [HIGH/MEDIUM/LOW]

**等待确认**: 是否按此计划执行？(yes/no/modify)
```

### 最佳实践

- 使用确切文件路径、函数名
- 考虑边界情况（空值、错误、边界条件）
- 最小化变更，优先扩展而非重写
- 遵循现有模式，保持一致性
- 每个步骤可独立验证

---

## 🔧 `/dev fix` - 构建修复 & 代码清理

修复构建错误 + 清理死代码和技术债务。

### 模式 1: 构建修复

```bash
# Python
uv run python -m py_compile app/main.py
uv run mypy app/

# TypeScript
npm run build
npx tsc --noEmit
```

对于每个错误：

1. 显示错误上下文（前后 5 行）
2. 解释问题原因
3. 提出修复方案
4. 应用修复
5. 重新构建验证
6. 确认无新错误

**停止条件**: 修复引入新错误 / 同一错误尝试 3 次 / 用户暂停

#### 常见 TypeScript 错误

| 代码   | 描述                | 修复          |
| ------ | ------------------- | ------------- |
| TS2304 | Cannot find name    | 添加 import   |
| TS2322 | Type mismatch       | 类型转换/修正 |
| TS2345 | Argument type error | 检查函数签名  |
| TS7006 | Implicit any        | 添加类型注解  |

#### 常见 Python 错误

| 类型        | 描述       | 修复              |
| ----------- | ---------- | ----------------- |
| ImportError | 模块未找到 | 安装依赖/修正路径 |
| TypeError   | 类型错误   | 检查参数类型      |
| SyntaxError | 语法错误   | 检查括号/缩进     |

### 模式 2: 代码清理

```bash
# Python
uv run ruff check . --select=F401,F841    # 未使用的 import/变量
uv run autoflake --in-place --remove-all-unused-imports app/
uv run vulture app/                        # 死代码检测

# TypeScript
npx eslint . --rule 'no-unused-vars: error'
npx knip                                   # 未使用的文件/依赖
npx eslint . --fix
```

清理对象：未使用的导入/变量/函数/类、注释掉的代码、无 issue 的 TODO/FIXME

清理步骤：扫描 → 分类（低/中/高风险） → 确认未使用 → 删除 → 运行测试 → 提交

### 修复摘要格式

```markdown
## 修复摘要

### 已修复 ✅

- [错误 1]: 文件:行号 - 描述

### 仍存在 ⚠️

- [错误 2]: 文件:行号 - 描述

### 新引入 ❌

- [错误 3]: 文件:行号 - 描述
```

**原则**: 一次修复一个错误，从根本原因开始，保留类型安全！

---

## 🧪 `/dev test` - 测试

TDD 工作流 + E2E 测试。最低覆盖率要求 **80%**。

### TDD 流程（强制）

```
1. RED    - 先写失败的测试
2. GREEN  - 写最少代码使测试通过
3. REFACTOR - 优化代码质量
4. VERIFY - 检查 80%+ 覆盖率
5. REPEAT
```

### 测试结构 (AAA 模式)

```python
def test_descriptive_name():
    # Arrange - 准备
    input_data = {"name": "Test", "age": 25}
    # Act - 执行
    result = process_user(input_data)
    # Assert - 断言
    assert result["is_valid"] is True
```

### 测试命名

```typescript
// ✅ Good
test("returns empty array when no items match query", () => {});
test("throws error when API key is missing", () => {});

// ❌ Bad
test("works", () => {});
test("test search", () => {});
```

### 覆盖率检查

```bash
# Python
uv run pytest --cov=app --cov-report=term-missing

# TypeScript
npm run test:coverage
```

### E2E 测试 (Playwright)

用于：认证/授权流程、支付流程、核心业务流程、多步骤表单

```typescript
// 推荐：页面对象模式
export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto("/login");
  }

  async login(email: string, password: string) {
    await this.page.fill('[data-testid="email"]', email);
    await this.page.fill('[data-testid="password"]', password);
    await this.page.click('[data-testid="submit"]');
  }
}
```

E2E 规则：

- ✅ 用 `data-testid` 定位、等待网络请求、隔离测试数据
- ❌ 不用 CSS 选择器、不用固定 `sleep`、不在测试间共享状态

```bash
npx playwright test           # 运行所有
npx playwright test --ui      # 带 UI
npx playwright show-report    # 报告
```

### 提交前测试检查

- [ ] 所有测试通过
- [ ] 覆盖率 80%+
- [ ] 测试名称描述性
- [ ] 测试隔离（无共享状态）
- [ ] Mock 正确配置

---

## 🔍 `/dev review` - 代码审查

对未提交变更进行全面审查。

### 流程

1. `git diff --name-only HEAD` 获取变更文件
2. 按优先级检查
3. 生成报告（CRITICAL / HIGH / MEDIUM / LOW）
4. CRITICAL 或 HIGH → 阻止提交

### 安全检查 (CRITICAL)

- [ ] 无硬编码凭证（API keys / passwords / tokens）
- [ ] 无 SQL 注入（无字符串拼接查询）
- [ ] 无 XSS 漏洞（用户输入已转义）
- [ ] 输入验证完整
- [ ] 无路径遍历

### 代码质量 (HIGH)

- [ ] 函数 ≤ 50 行、文件 ≤ 800 行
- [ ] 嵌套 ≤ 4 层
- [ ] 无空 try/catch
- [ ] 无 console.log
- [ ] 公共 API 有 JSDoc

### 性能 (MEDIUM)

- [ ] 无 O(n²) 可优化场景
- [ ] 无不必要的 React 重渲染
- [ ] 无 N+1 查询
- [ ] 热点数据有缓存

### 最佳实践 (MEDIUM)

- [ ] 使用不可变模式
- [ ] 新代码有测试
- [ ] 变量命名清晰
- [ ] 无 magic number

### 审查工具

```bash
# Python
uv run ruff check .
uv run mypy app/
uv run bandit -r app/

# TypeScript
npm run lint
npm run type-check
```

### 审批标准

- ✅ 批准: 无 CRITICAL/HIGH
- ⚠️ 警告: 仅 MEDIUM（可谨慎合并）
- ❌ 阻止: 发现 CRITICAL/HIGH

---

## 🔄 `/dev git` - Git 工作流

### Commit 格式

```
<type>: <description>

类型: feat | fix | refactor | docs | test | chore | perf | ci
```

```bash
# ✅ Good
git commit -m "feat: add semantic search for markets"
git commit -m "fix: prevent duplicate creation by adding unique constraint"

# ❌ Bad
git commit -m "fix: bug"
git commit -m "feat: added search"  # 用现在时态
```

### 分支命名

```
<type>/<short-description>

feature/semantic-search
fix/cache-race-condition
refactor/user-service
```

### PR 前检查

```bash
git checkout main; git pull origin main
git checkout feature/my-feature; git rebase main
uv run pytest tests/
uv run ruff check .; uv run ruff format .
```

### 提交前检查

- [ ] 编译/运行无错误
- [ ] 所有测试通过
- [ ] 无 console.log / debug 语句
- [ ] 无硬编码密钥
- [ ] 无不必要文件
- [ ] 注释解释 WHY 不是 WHAT
- [ ] 原子提交（一个 commit = 一个逻辑变更）

---

## 🧩 `/dev skill` - Skill 管理

### 创建新 Skill

目录结构：

```
skill-name/
├── SKILL.md          (必须 - 主文件)
├── references/       (可选 - 详细文档)
└── scripts/          (可选 - 辅助脚本)
```

SKILL.md 格式：

```yaml
---
name: skill-name
description: 功能说明 + 触发条件。Use when (1)..., (2)..., (3)...
---
```

规范：

- `name` 匹配目录名
- `description` ≤ 100 词，包含触发条件
- 正文用祈使句（"Read the file"）
- 正文 ≤ 500 行，详细内容放 `references/`

### Skill 关键词映射

| 关键词                             | Skill                      |
| ---------------------------------- | -------------------------- |
| fastapi, backend, python api, 后端 | `dev-senior_backend`       |
| react, frontend, typescript, 前端  | `dev-senior_frontend`      |
| testing, unit test, pytest, 测试   | `dev-senior_qa`            |
| architecture, system design, 架构  | `dev-senior_architect`     |
| fullstack, 全栈                    | `dev-senior_fullstack`     |
| devops, ci/cd, docker, 部署        | `dev-senior_devops`        |
| data pipeline, etl, 数据工程       | `dev-senior_data_engineer` |
| product, prd, user story, 产品     | `dev-product_manager`      |
| code review, 代码审查              | `dev-code_reviewer`        |
| template extraction, 模板提取      | `dev-template_extraction`  |

匹配规则：自动检测关键词 → 加载最匹配的 skill → 静默应用

---

## 📚 参考资料（按需查阅）

### 代码规范

```
.agent/skills/dev-code_reviewer/references/
├── code-quality-standards.md    # 代码质量标准
├── security-guidelines.md       # 安全指南
├── design-patterns.md           # 设计模式
├── performance-guidelines.md    # 性能优化
└── review-checklist.md          # 审查清单
```

### 教科书知识库（51 本）

```
data/mineru_output/                    # MineRU 解析后的教科书 Markdown
├── ramalho_fluent_python/             # Python 高级编程
├── beazley_python_cookbook/            # Python 实用配方
├── okken_python_testing_pytest/       # pytest 测试
├── flanagan_js_definitive_guide/      # JavaScript 权威指南
├── basarat_typescript_deep_dive/      # TypeScript 深入
├── simpson_ydkjs_*/                   # YDKJS 系列（6 本）
├── cormen_CLRS/                       # 算法导论
├── martin_clean_code/                 # 代码整洁之道
├── martin_clean_architecture/         # 架构整洁之道
├── kleppmann_ddia/                    # 数据密集型应用设计
├── gof_design_patterns/               # 设计模式
├── fowler_refactoring/                # 重构
├── hunt_pragmatic_programmer/         # 程序员修炼之道
├── google_swe/                        # Google 软件工程
├── chacon_pro_git/                    # Pro Git
├── google_sre/                        # 站点可靠性工程
├── nygard_release_it/                 # Release It!
├── goodfellow_deep_learning/          # 深度学习
├── bishop_prml/                       # 模式识别与机器学习
├── krug_dont_make_me_think/           # 可用性设计
├── norman_design_everyday_things/     # 日常设计
└── ... (共 51 本，完整列表见 textbooks/README.md)

textbooks/topic_index.json             # 52 个主题 → 266 个章节索引（50 本）
.agent/config/textbook-skill-mapping.yaml  # Skill ↔ Textbook 映射
```

重建索引: `uv run python scripts/rebuild_topic_index.py`
如需详细参考，使用 `view_file` 读取对应文件。

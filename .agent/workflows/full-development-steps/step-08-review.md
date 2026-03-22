# Step 8: 代码审查

## 阶段信息

- **阶段**: `review` - 代码审查
- **Skill**: `dev-code_reviewer`
- **输入**: `backend/`, `frontend/`, `backend/tests/`
- **产出物**: `docs/review-report.md`

---

## 执行步骤

### 1. 加载上下文

读取并分析：

- `docs/architecture/system-architecture.md` - 架构规范
- `docs/sprints/sprint-plan.md` - 功能需求
- `backend/app/` - 后端源代码
- `frontend/src/` - 前端源代码
- `backend/tests/` - 测试代码

### 2. 加载 Skill

加载 `dev-code_reviewer` skill，获取代码审查专业知识。

### 3. 🎯 脚本查找 (Template-First)

**在审查之前，先运行自动化检查脚本：**

| 脚本                 | 命令                                                      | 用途               |
| -------------------- | --------------------------------------------------------- | ------------------ |
| `env_check.py`       | `python .agent/scripts/env_check.py --files`              | 检查配置文件完整性 |
| `coverage_report.py` | `python .agent/scripts/coverage_report.py --threshold 80` | 验证测试覆盖率     |
| `extract_i18n.py`    | `python .agent/scripts/extract_i18n.py --check`           | 检查缺失的翻译键   |

运行顺序：

1. 先运行上述脚本，收集自动化检查结果
2. 将脚本结果纳入审查报告
3. 再执行人工审查维度

### 4. 审查维度

| 维度           | 权重 | 说明             |
| -------------- | ---- | ---------------- |
| **功能正确性** | 30%  | 是否满足需求     |
| **代码质量**   | 25%  | 可读性、可维护性 |
| **安全性**     | 20%  | 安全漏洞检查     |
| **性能**       | 15%  | 性能问题检查     |
| **测试覆盖**   | 10%  | 测试充分性       |

### 4. 自动化检查

运行自动化工具：

```bash
# 后端代码风格
cd backend && uv run ruff check app/

# 前端代码风格
cd frontend && npm run lint

# 后端类型检查
cd backend && uv run mypy app/ --ignore-missing-imports

# 前端类型检查
cd frontend && npx tsc --noEmit

# 安全扫描
cd frontend && npm audit
cd backend && uv run pip-audit
```

### 5. 安全审查

#### 5.1 OWASP Top 10 检查

- [ ] **注入攻击** - SQL/NoSQL/命令注入
- [ ] **认证缺陷** - 弱密码、会话管理
- [ ] **敏感数据泄露** - 加密、传输安全
- [ ] **XXE** - XML 外部实体
- [ ] **访问控制** - 权限检查
- [ ] **安全配置错误** - 默认配置
- [ ] **XSS** - 跨站脚本
- [ ] **反序列化** - 不安全的反序列化
- [ ] **组件漏洞** - 已知漏洞组件
- [ ] **日志监控** - 日志和监控不足

#### 5.2 敏感信息检查

```bash
# 检查硬编码密钥
grep -r "password\|secret\|api_key" backend/app/ --include="*.py"
grep -r "password\|secret\|api_key" frontend/src/ --include="*.ts" --include="*.tsx"

# 检查 .env 文件
test -f backend/.env && echo "警告: .env 文件存在，确保已加入 .gitignore"
```

### 6. 性能审查

#### 6.1 后端性能

- [ ] N+1 查询问题
- [ ] 缺少数据库索引
- [ ] 大量内存分配
- [ ] 阻塞操作
- [ ] 缺少缓存

#### 6.2 前端性能

- [ ] 大型 Bundle
- [ ] 未优化图片
- [ ] 缺少懒加载
- [ ] 不必要的重渲染
- [ ] 内存泄漏

### 7. 代码质量审查

#### 7.1 命名规范

```
✓ 变量名语义清晰
✓ 函数名描述行为
✓ 类名使用名词
✓ 常量使用大写
```

#### 7.2 代码结构

```
✓ 函数长度 < 50 行
✓ 类长度 < 300 行
✓ 文件长度 < 500 行
✓ 循环嵌套 < 3 层
✓ 圈复杂度 < 10
```

#### 7.3 最佳实践

```
✓ DRY - 无重复代码
✓ SOLID 原则
✓ 错误处理完善
✓ 日志记录合理
✓ 注释清晰
```

### 8. 问题分类

| 严重性      | 说明                   | 处理     |
| ----------- | ---------------------- | -------- |
| 🔴 Critical | 安全漏洞、数据丢失风险 | 必须修复 |
| 🟠 Major    | 功能缺陷、性能问题     | 应该修复 |
| 🟡 Minor    | 代码风格、小改进       | 建议修复 |
| 🔵 Info     | 信息提示、文档建议     | 可选修复 |

### 9. 生成报告

创建 `docs/review-report.md`：

```markdown
# 代码审查报告

## 概览

- 审查日期: {date}
- 代码版本: {commit_hash}
- 审查范围: src/, tests/

## 评分

| 维度       | 得分       | 说明       |
| ---------- | ---------- | ---------- |
| 功能正确性 | 9/10       | 满足需求   |
| 代码质量   | 8/10       | 良好       |
| 安全性     | 9/10       | 无严重漏洞 |
| 性能       | 7/10       | 有优化空间 |
| 测试覆盖   | 8/10       | 覆盖率达标 |
| **总分**   | **82/100** | **通过**   |

## 发现问题

### 🔴 Critical (0)

无

### 🟠 Major (2)

1. **[BE-001] N+1 查询问题**
   - 文件: `src/backend/services/order_service.py:45`
   - 描述: 循环中查询用户信息
   - 建议: 使用 joinedload 预加载

2. **[FE-001] XSS 风险**
   - 文件: `src/frontend/components/Comment.tsx:23`
   - 描述: 使用 dangerouslySetInnerHTML
   - 建议: 使用 DOMPurify 清理

### 🟡 Minor (5)

1. ...

### 🔵 Info (3)

1. ...

## 修复建议

### 必须修复 (阻断发布)

- [ ] 修复 N+1 查询
- [ ] 修复 XSS 风险

### 建议修复 (下个版本)

- [ ] 优化图片加载
- [ ] 添加缓存

## 结论

代码整体质量良好，需修复 2 个 Major 问题后可发布。
```

### 10. 问题修复

对于 Critical 和 Major 问题：

```
┌─────────────────────────────────────────────┐
│  Issue: [BE-001] N+1 查询问题               │
├─────────────────────────────────────────────┤
│  1. 定位问题代码                            │
│  2. 应用修复                                │
│  3. 添加/更新测试                           │
│  4. 重新审查                                │
│  5. 标记已修复                              │
└─────────────────────────────────────────────┘
```

### 11. 用户确认

```
审查发现:
- 🔴 Critical: 0
- 🟠 Major: 2 (已修复)
- 🟡 Minor: 5
- 🔵 Info: 3

[C] 确认 - 审查通过，继续下一阶段
[F] 修复 - 继续修复问题
[R] 重审 - 重新审查
```

---

## 完成检查

- [ ] 自动化检查通过
- [ ] 安全审查通过
- [ ] Critical 问题: 0
- [ ] Major 问题已修复
- [ ] 审查报告已生成

## 状态更新

```yaml
current_phase: deployment

phases:
  review:
    status: completed
    completed_at: "{current_time}"
    output: "docs/review-report.md"
```

## 下一步

→ 进入 `step-09-deployment.md`

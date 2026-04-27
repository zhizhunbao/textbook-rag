# Sprint Robustness — 用 LlamaIndex `structured_predict` 替换裸 JSON 解析

> 目标：用 LlamaIndex 自带的 `llm.structured_predict()` 替换所有手写 `json.loads` 调用，消除 LLM 输出解析崩溃风险。
> 零新依赖 — 全部能力已内建于 `llama-index-core`。
>
> 前置条件：无硬依赖。可独立执行。
> **状态**: ✅ 5/5 完成

## 为什么用 `structured_predict` 而不是手写 parser

LlamaIndex `llm.structured_predict()` 内部已实现完整防御链：

```
1. PydanticOutputParser.format()    → 自动注入 JSON Schema 到 prompt
2. extract_json_str()               → 正则提取 {...} 边界
3. parse_json_markdown()            → 剥离 ```json ``` fence
4. yaml.safe_load() fallback        → 处理 trailing comma 等常见错误
5. _repair_incomplete_json()        → 修补未闭合引号/括号（截断输出）
6. model_validate_json()            → Pydantic 类型校验 + 约束检查
7. get_program_for_llm() auto-route → 模型支持 function calling 则走 tool call，否则走文本解析
```

源码位置（已验证）：
- `llama_index.core.llms.llm.LLM.structured_predict` — 主入口
- `llama_index.core.output_parsers.pydantic.PydanticOutputParser` — schema 注入 + 解析
- `llama_index.core.output_parsers.utils.parse_json_markdown` — fence 剥离 + yaml fallback
- `llama_index.core.program.utils.get_program_for_llm` — 策略路由

**不需要 `instructor`、`json-repair`、或自写 `output_guard.py`。**

## 概览

| Task | Story 数 | 预估总工时 | 说明 |
|------|----------|-----------|------|
| T1 Pydantic Schemas | 1 | 0.5h | 定义 QuestionItem + QuestionScoreOutput |
| T2 Generator 重构 | 2 | 1.5h | `_parse_scores` + `_parse_response` → `structured_predict` |
| T3 Classify 重构 | 2 | 1h | `classify_book` → `structured_predict` |
| **合计** | **5** | **3h** |

## 质量门禁

| # | 检查项 | 判定依据 |
|---|--------|----------|
| G1 | 零新依赖 | 仅用 `llama_index.core` 已有 API，不加任何 pip package |
| G2 | 零功能回归 | 替换后所有现有功能行为不变；新增的是容错能力 |
| G3 | Surgical Changes | 只改调用点，不重构无关代码 |
| G4 | 框架对齐 | 使用 LlamaIndex 官方 `structured_predict` API，与项目技术栈一致 |

---

## [RB-T1] Pydantic Schemas

### [RB-T1-01] 定义 QuestionItem + QuestionScoreOutput

**类型**: Backend · **优先级**: P0 · **预估**: 0.5h

**描述**: 为 `generator.py` 的两处 JSON 解析定义 Pydantic models。

```python
from pydantic import BaseModel, Field

class QuestionItem(BaseModel):
    """Single generated study question."""
    question: str
    difficulty: str = "medium"
    type: str = "conceptual"
    question_category: str = ""

class QuestionScoreOutput(BaseModel):
    """LLM-as-Judge scoring result."""
    relevance: int = Field(default=1, ge=1, le=5)
    clarity: int = Field(default=1, ge=1, le=5)
    difficulty: int = Field(default=1, ge=1, le=5)
    reasoning: str = ""
```

**验收标准**:
- [x] 在 `engine_v2/question_gen/generator.py` 顶部定义（就近原则）
- [x] `QuestionItem.question` 为必填字段
- [x] `QuestionScoreOutput` 的三个 int 字段有 `ge=1, le=5` 约束
- [x] 默认值确保 Pydantic 在字段缺失时不崩溃

**文件**: `engine_v2/question_gen/generator.py`

---

## [RB-T2] Generator 重构

### [RB-T2-01] _parse_scores() → structured_predict

**类型**: Backend · **优先级**: P0 · **预估**: 0.5h

**描述**: 将 `_parse_scores()` 的裸 JSON 解析替换为 `llm.structured_predict(QuestionScoreOutput, ...)`。

**当前代码** (`generator.py:210-238`):
```python
# 手写 JSON 提取 + json.loads + int() 强转
text = text.strip()
start = text.find("{")
end = text.rfind("}") + 1
data = json.loads(text[start:end])       # ← 裸解析
relevance = int(data.get("relevance", 0)) # ← 强转，LLM 返回 "4/5" 即崩溃
```

**改为**: 在 `score_questions()` 中直接调用 `structured_predict`，跳过手动解析：
```python
from llama_index.core.prompts import PromptTemplate

SCORE_PROMPT_TEMPLATE = PromptTemplate(QUESTION_SCORE_PROMPT)

# 在 score_questions() 中:
parsed = Settings.llm.structured_predict(
    QuestionScoreOutput,
    SCORE_PROMPT_TEMPLATE,
    context=context_str,
    question=q.question,
)
# parsed 直接就是 QuestionScoreOutput 实例
q.scores = QuestionScores(
    relevance=parsed.relevance,
    clarity=parsed.clarity,
    difficulty=parsed.difficulty,
    overall=round((parsed.relevance + parsed.clarity) / 2, 1),
    reasoning=parsed.reasoning,
)
```

**验收标准**:
- [x] `_parse_scores()` 方法删除或标记 deprecated
- [x] 改用 `Settings.llm.structured_predict(QuestionScoreOutput, ...)`
- [x] 不再有任何 `json.loads` 或 `int()` 强转
- [x] QUESTION_SCORE_PROMPT 转为 `PromptTemplate`（使用 `{var}` 占位符）
- [x] 解析失败时仍返回默认 `QuestionScores()`（try/except 保持）
- [x] G2 ✅ 零功能回归

**文件**: `engine_v2/question_gen/generator.py`

### [RB-T2-02] _parse_response() → structured_predict (list)

**类型**: Backend · **优先级**: P0 · **预估**: 1h

**描述**: 将 `_parse_response()` 的裸 JSON array 解析替换为 `structured_predict`。

**难点**: `structured_predict` 返回单个 Pydantic 实例，不直接支持数组。LlamaIndex 内建了 `create_list_model()` 工具：

```python
from llama_index.core.program.utils import create_list_model

QuestionItemList = create_list_model(QuestionItem)
# 生成: class QuestionItemList(BaseModel): items: List[QuestionItem]

GEN_PROMPT_TEMPLATE = PromptTemplate(QUESTION_GEN_PROMPT)

result = Settings.llm.structured_predict(
    QuestionItemList,
    GEN_PROMPT_TEMPLATE,
    count=count,
    context=context_str,
)
# result.items 是 list[QuestionItem]
```

**当前代码** (`generator.py:318-354`):
```python
text = text.strip()
start = text.find("[")
end = text.rfind("]") + 1
items = json.loads(text[start:end])  # ← 裸解析，无容错
```

**验收标准**:
- [x] `_parse_response()` 方法删除或标记 deprecated
- [x] 改用 `structured_predict(QuestionItemList, ...)` 
- [x] QUESTION_GEN_PROMPT 转为 `PromptTemplate`（`{count}`, `{context}` 占位符）
- [x] 返回值仍为 `list[GeneratedQuestion]`（从 `QuestionItem` 映射）
- [x] chunk metadata 映射逻辑保持不变
- [x] G2 ✅ 零功能回归
- [x] G4 ✅ 使用 LlamaIndex 官方 `create_list_model`

**文件**: `engine_v2/question_gen/generator.py`

---

## [RB-T3] Classify 重构

### [RB-T3-01] classify_book() → structured_predict

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**描述**: 将 `classify_book()` 的手动 fence 剥离 + `json.loads` 替换为 `structured_predict`。

**当前代码** (`classify.py:97-113`):
```python
response = llm.complete(prompt)
raw_text = response.text.strip()
if raw_text.startswith("```"):  # ← 手动 fence 剥离
    lines = raw_text.split("\n")
    lines = [ln for ln in lines if not ln.startswith("```")]
    raw_text = "\n".join(lines).strip()
result = json.loads(raw_text)   # ← 裸解析
category = str(result.get("category", "textbook")).lower().strip()  # ← 手动类型转换
```

**改为**:
```python
from llama_index.core.prompts import PromptTemplate

class ClassifyOutput(BaseModel):
    """LLM classification result."""
    category: str = Field(default="textbook", description="Lowercase category")
    subcategory: str = Field(default="", description="Title Case subcategory")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)

CLASSIFY_PROMPT_TEMPLATE = PromptTemplate(CLASSIFY_PROMPT)

result = llm.structured_predict(
    ClassifyOutput,
    CLASSIFY_PROMPT_TEMPLATE,
    title=req.title,
    filename=req.filename or "(not provided)",
)
# result 直接就是 ClassifyOutput 实例，类型安全
```

**验收标准**:
- [x] 移除手动 markdown fence 剥离逻辑（`structured_predict` 内部已处理）
- [x] 移除 `json.loads` + 手动 `.get()` + `str()`/`float()` 强转
- [x] `ClassifyResponse` 直接复用为 output_cls（`field_validator` 处理 normalize）
- [x] CLASSIFY_PROMPT 转为 `PromptTemplate`（`{title}`, `{filename}` 占位符）
- [x] 解析失败仍 fallback 到 `_heuristic_classify()`（现有行为保持）
- [x] G2 ✅ 零功能回归

**文件**: `engine_v2/api/routes/classify.py`

### [RB-T3-02] ClassifyResponse 复用清理

**类型**: Backend · **优先级**: P1 · **预估**: 0.5h

**描述**: 评估是否可以直接用现有的 `ClassifyResponse` 作为 `structured_predict` 的 output_cls。如果字段兼容，删除新增的 `ClassifyOutput`，直接复用。

当前 `ClassifyResponse`:
```python
class ClassifyResponse(BaseModel):
    category: str
    subcategory: str
    confidence: float
```

**验收标准**:
- [x] `ClassifyResponse` 字段与 LLM 输出 1:1 对应，直接复用
- [x] 后处理（lowercase、title_case）在 Pydantic `field_validator` 中处理
- [x] 最终只有一个 Classify schema — `ClassifyResponse`（不重复定义）

**文件**: `engine_v2/api/routes/classify.py`

---

## 模块文件变更

```
engine_v2/
├── question_gen/
│   └── generator.py       ← 改造 (Pydantic schemas + structured_predict)
└── api/routes/
    └── classify.py         ← 改造 (structured_predict + schema 复用)
```

**零新文件** — 没有 `output_guard.py`，没有新模块。

---

## Prompt 转换注意事项

`structured_predict` 使用 LlamaIndex 的 `PromptTemplate`，占位符格式为 `{var}`。
当前 prompt 中的 `{{` / `}}` JSON 示例需改为单括号，因为 `PromptTemplate` 使用 Python f-string 风格。

**转换示例**:
```python
# 之前（raw string，手动 .format()）:
QUESTION_SCORE_PROMPT = """... Score as JSON: {{"relevance": <int>, ...}}"""
prompt = QUESTION_SCORE_PROMPT.format(context=ctx, question=q)

# 之后（PromptTemplate，LlamaIndex 管理格式化）:
SCORE_PROMPT_TMPL = PromptTemplate(
    "... Score as JSON: {\"relevance\": <int>, ...}\n"
    "Context: {context}\nQuestion: {question}"
)
# structured_predict 自动追加 JSON Schema 说明
result = llm.structured_predict(QuestionScoreOutput, SCORE_PROMPT_TMPL, context=ctx, question=q)
```

> **重要**: `PydanticOutputParser` 会自动在 prompt 末尾追加 `"Here's a JSON schema to follow: {schema}\nOutput a valid JSON object but do not repeat the schema."`。
> 所以 prompt 中不需要再手写 JSON 格式说明 — **框架帮你做了**。

---

## 执行顺序

| Phase | Tasks | Est. Time | 前置 | 备注 |
|-------|-------|-----------|------|------|
| **Phase 1** | RB-T1-01 (schemas) | 0.5h | 无 | 定义 Pydantic models |
| **Phase 2** | RB-T2-01, RB-T2-02 (generator) | 1.5h | Phase 1 | 最高风险点 |
| **Phase 3** | RB-T3-01, RB-T3-02 (classify) | 1h | 无 | 独立可做 |

---

## 与其他 Sprint 的关系

| Sprint | 关系 | 说明 |
|--------|------|------|
| Sprint EV2 (16) | **独立** | 评估 prompt 走 LlamaIndex `CorrectnessEvaluator` 内部解析，不在范围 |
| Sprint QD (13) | **增强** | Question Dataset 依赖 `generator.py`，本 Sprint 加固后稳定性直接受益 |
| Sprint S5-S8 | **标准** | 未来新增 LLM 结构化输出统一使用 `structured_predict`，不再裸写 `json.loads` |

---

## Exclusions — 不在范围内

| 模块 | 原因 |
|------|------|
| `evaluation/prompts.py` | 被 LlamaIndex `CorrectnessEvaluator` 消费，有自己的解析逻辑 |
| `evaluation/evaluator.py` | 同上 |
| `response_synthesizers/*` | 自由文本生成，无需结构化解析 |
| `query_engine/intent.py` | 纯规则分类，无 LLM 调用 |
| `instructor` / `json-repair` | 不需要 — LlamaIndex 内建能力已覆盖 |

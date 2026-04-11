# `question_gen` — 问题引擎

> 不是出题工具，是 chat 的上游供给系统。

```
Layout
书籍选择
题目列表

UI
书籍选框
生成按钮
题目卡片
推荐卡片

UX
选书生成
批量浏览
难度筛选
推荐引导

Func
自动出题
多类题型
知识覆盖
去重校验
问题推荐                按章节生成推荐问题，供 chat WelcomeScreen 消费
质量评估                判断问题深度 (surface / understanding / synthesis)
重复检测                向量相似度匹配历史问题，引导深入

Noun
Question
Book
Generate
Type
Difficulty
Answer
Option
Coverage
Suggest
Quality
Depth
Duplicate
Similar
Recommend
Hint
```

```
question_gen
├── engine_v2/question_gen/
│   ├── __init__.py                         re-export 公共 API
│   ├── generator.py                        LLM 自动出题
│   ├── quality.py                          问题深度评估器                  ← NEW
│   └── dedup.py                            向量相似度去重                  ← NEW
├── engine_v2/api/routes/
│   ├── questions.py                        题目 CRUD + 生成端点
│   └── suggest.py                          推荐问题端点 (GET /engine/questions/suggest)
├── payload-v2/src/collections/
│   └── Questions.ts                        题目 Collection
├── payload-v2/src/features/engine/question_gen/
│   ├── index.ts                            barrel export
│   ├── types.ts                            Question 等类型
│   ├── api.ts                              题目 + 推荐 + 质量 API
│   ├── useQuestionGeneration.ts            生成 + 保存 hook
│   ├── useSuggestedQuestions.ts            推荐问题 hook (供 chat 消费)
│   ├── useBooks.ts                         可选书籍列表 hook
│   └── components/
│       ├── QuestionsPage.tsx               题目库页面 (卡片 + 表格双视图)
│       ├── QuestionCards.tsx               题目卡片 (Markdown + 评分)
│       ├── GenerationProgress.tsx          生成进度展示
│       ├── BookSelector.tsx                书籍多选器 (触发生成)
│       ├── GenerationPanel.tsx             生成面板 (选书+生成+进度)
│       └── SuggestedQuestions.tsx          推荐问题卡片 (供 chat 嵌入)
└── payload-v2/src/app/(frontend)/engine/question_gen/
    └── page.tsx                            /engine/question_gen 路由薄壳
```

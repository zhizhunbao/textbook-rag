# `chat` — RAG 对话

```
Layout
三栏布局
历史侧栏＋对话主体＋问题侧栏

UI
消息气泡
输入面板
历史列表
推荐问题
Prompt 选择

UX
流式输出
上下文切换
溯源引用
Prompt 切换
问题浏览

Func
检索增强
对话管理
来源追溯
全链编排

Noun
Chat
Message
Conversation
History
Source
Context
Input
Stream
Prompt
Suggest
```

```
chat
├── payload-v2/src/features/chat/
│   ├── ChatPage.tsx                        对话页面 (PDF 左 + Chat 中 + 问题右)
│   ├── types.ts                            Message 等类型
│   ├── history/
│   │   ├── index.ts                        barrel export
│   │   ├── ChatHistoryContext.tsx           会话历史 Context
│   │   ├── ChatHistoryPanel.tsx            历史列表侧栏
│   │   └── useChatHistory.ts              会话持久化 hook
│   ├── questions/
│   │   ├── index.ts                        barrel export
│   │   ├── QuestionSidebar.tsx             右侧问题侧栏 (按分类)          ← NEW
│   │   └── QuestionItem.tsx               单个问题卡片 (点击即提问)       ← NEW
│   └── panel/
│       ├── index.ts                        barrel export
│       ├── ChatPanel.tsx                   对话面板 (消息列表 + 输入)
│       ├── ChatHeader.tsx                  对话顶栏 (文档名 + LLM + Prompt)
│       ├── ChatInput.tsx                   输入框 + 发送按钮
│       ├── MessageBubble.tsx               AI / 用户消息气泡
│       ├── PromptSelector.tsx              Prompt 模式选择器               ← NEW (替代 ModeToggle)
│       ├── SourceCard.tsx                  来源引用卡片
│       └── WelcomeScreen.tsx              欢迎页 (选文档前)
└── payload-v2/src/app/(frontend)/chat/
    └── page.tsx                            /chat 路由薄壳
```

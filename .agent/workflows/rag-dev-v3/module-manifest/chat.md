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
检索增强 (RAG)
对话管理 (Sessions)
来源追溯 (Citations)
全链编排 (Orchestration)
专家人设 (Personas)           ← NEW
双库联合检索 (Dual-retrieval)   ← NEW

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
Persona                       ← NEW
Consulting                    ← NEW
UserDocument                  ← NEW
```

```
chat
├── payload-v2/src/features/chat/
│   ├── ChatPage.tsx                        标准对话页面 (教科书场景)
│   ├── types.ts                            Message 等类型
│   ├── history/
│   │   ├── ChatHistoryContext.tsx           会话历史管理
│   │   └── useChatHistory.ts              会话持久化 hook
│   └── panel/
│       ├── ChatPanel.tsx                   对话主体 (消息列表 + 输入)
│       ├── MessageBubble.tsx               气泡组件 (支持 Origin 标签)
│       ├── ChatInput.tsx                   输入框
│       └── SourceCard.tsx                  引用卡片
├── payload-v2/src/features/consulting/     专家咨询子模块 (复用 chat 组件)
│   ├── ConsultingChatPage.tsx              专家对话页面 (咨询场景)
│   ├── api.ts                              咨询专用 API (Dual-retrieval)
│   └── user-docs/                          用户私有文档管理
└── payload-v2/src/app/(frontend)/
    ├── chat/page.tsx                       标准对话路由
    └── consulting/page.tsx                 专家咨询路由
```

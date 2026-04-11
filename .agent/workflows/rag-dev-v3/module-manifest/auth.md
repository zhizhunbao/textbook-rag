# `auth` — 登录认证

```
Layout
居中表单
全屏背景

UI
邮箱密码
登录按钮
错误提示

UX
即时校验
回车提交
加载反馈

Func
凭证验证
令牌存储
会话管理

Noun
Auth
User
Token
Session
Credential
Login
```

```
auth
├── payload-v2/src/features/auth/
│   └── LoginForm.tsx                       居中登录表单
├── payload-v2/src/features/shared/
│   └── AuthProvider.tsx                    JWT 认证 Context + useAuth
├── payload-v2/src/collections/
│   └── Users.ts                            用户 Collection
├── payload-v2/src/access/
│   ├── isAdmin.ts                          管理员访问策略
│   ├── isEditorOrAdmin.ts                  编辑者访问策略
│   └── isOwnerOrAdmin.ts                   属主访问策略
└── payload-v2/src/app/(frontend)/login/
    └── page.tsx                            /login 路由薄壳
```

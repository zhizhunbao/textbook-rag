# `access` — 权限控制

> 纯后端模块，无前端 UI。

```
Func
角色鉴权
管理独占
编辑可写
属主可改

Noun
Access
Role
Policy
Permission
Guard
```

```
access
└── payload-v2/src/access/
    ├── isAdmin.ts                          管理员访问策略
    ├── isEditorOrAdmin.ts                  编辑者访问策略
    └── isOwnerOrAdmin.ts                   属主访问策略
```

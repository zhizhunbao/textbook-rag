# Textbook-RAG v2 — 文件模板索引

> 本文档是所有文件模板的索引。每个模板存放在 `file-templates/` 目录下，按需加载。
> 文件角色与命名规则详见 [`project-structure.md`](./project-structure.md)。

---

## 一、Python 层

| #    | 模板文件 | 对应路径 | 说明 |
| ---- | -------- | -------- | ---- |
| 1.1  | [py-module-init.md](./file-templates/py-module-init.md) | `engine_v2/<module>/__init__.py` | 功能模块入口 |
| 1.2  | [py-module-impl.md](./file-templates/py-module-impl.md) | `engine_v2/<module>/<impl>.py` | 模块实现 |
| 1.3  | [py-root-init.md](./file-templates/py-root-init.md) | `engine_v2/__init__.py` | 根包入口 (参考) |
| 1.4  | [py-schema.md](./file-templates/py-schema.md) | `engine_v2/schema.py` | 领域模型 (参考) |
| 1.5  | [py-errors.md](./file-templates/py-errors.md) | `engine_v2/errors.py` | 自定义异常层级 (参考) |
| 1.6  | [py-settings.md](./file-templates/py-settings.md) | `engine_v2/settings.py` | 全局配置单例 (参考) |
| 1.7  | [py-api-route.md](./file-templates/py-api-route.md) | `engine_v2/api/routes/<resource>.py` | API 路由 |
| 1.8  | [py-api-middleware.md](./file-templates/py-api-middleware.md) | `engine_v2/api/middleware/<concern>.py` | 中间件 |
| 1.9  | [py-script.md](./file-templates/py-script.md) | `scripts/<verb>_<noun>.py` | 独立脚本 |

---

## 二、Payload CMS 层

| #    | 模板文件 | 对应路径 | 说明 |
| ---- | -------- | -------- | ---- |
| 2.1  | [cms-collection.md](./file-templates/cms-collection.md) | `collections/<CollectionName>.ts` | Collection 定义 |
| 2.2  | [cms-endpoint.md](./file-templates/cms-endpoint.md) | `collections/endpoints/<endpoint-name>.ts` | 自定义端点 |
| 2.3  | [cms-endpoint-barrel.md](./file-templates/cms-endpoint-barrel.md) | `collections/endpoints/index.ts` | Barrel Export |
| 2.4  | [cms-hook.md](./file-templates/cms-hook.md) | `hooks/<collection>/<lifecycle>.ts` | 生命周期钩子 |
| 2.5  | [cms-access.md](./file-templates/cms-access.md) | `access/is<Role>.ts` | 访问控制策略 |
| 2.6  | [cms-seed.md](./file-templates/cms-seed.md) | `seed/<data-source>.ts` | 预置数据源 |

---

## 三、React 前端层

| #    | 模板文件 | 对应路径 | 说明 |
| ---- | -------- | -------- | ---- |
| 3.1  | [react-page.md](./file-templates/react-page.md) | `app/(frontend)/<page>/page.tsx` | 路由页面 (薄壳) |
| 3.2  | [react-page-dynamic.md](./file-templates/react-page-dynamic.md) | `app/(frontend)/<page>/[<paramId>]/page.tsx` | 动态路由页面 |
| 3.3  | [react-provider.md](./file-templates/react-provider.md) | `features/providers/<Name>Provider.tsx` | 全局 Provider |
| 3.4  | [react-context.md](./file-templates/react-context.md) | `features/providers/<Name>Context.tsx` | 独立 Context |
| 3.5  | [react-providers-root.md](./file-templates/react-providers-root.md) | `features/providers/Providers.tsx` | 组合根 (参考) |
| 3.6  | [react-messages.md](./file-templates/react-messages.md) | `features/providers/messages.ts` | i18n 翻译字典 (参考) |
| 3.7  | [react-shared-types.md](./file-templates/react-shared-types.md) | `features/shared/types.ts` | 全局类型定义 (参考) |
| 3.8  | [react-shared-utils.md](./file-templates/react-shared-utils.md) | `features/shared/utils.ts` | 纯工具函数 (参考) |
| 3.9  | [react-shared-hook.md](./file-templates/react-shared-hook.md) | `features/shared/hooks/use<Name>.ts` | 共享 Hook |
| 3.10 | [react-shared-config.md](./file-templates/react-shared-config.md) | `features/shared/config/<name>.ts` | 前端配置 |
| 3.11 | [react-shared-lib.md](./file-templates/react-shared-lib.md) | `features/shared/lib/<library>.ts` | 第三方库封装 |
| 3.12 | [react-shared-component.md](./file-templates/react-shared-component.md) | `features/shared/components/<ComponentName>.tsx` | 通用组件 |
| 3.13 | [react-shared-ui.md](./file-templates/react-shared-ui.md) | `features/shared/components/ui/<component-name>.tsx` | 原子 UI 组件 |
| 3.14 | [react-shared-chart.md](./file-templates/react-shared-chart.md) | `features/shared/components/charts/<chart-type>.tsx` | 图表组件 |
| 3.15 | [react-shared-api-client.md](./file-templates/react-shared-api-client.md) | `features/shared/api/client.ts` | 统一 fetch 封装 (参考) |
| 3.16 | [react-shared-api-types.md](./file-templates/react-shared-api-types.md) | `features/shared/api/types.ts` | API 层类型 (参考) |
| 3.17 | [react-layout.md](./file-templates/react-layout.md) | `features/layout/App<Part>.tsx` | App Shell 组件 |
| 3.18 | [react-feature-page.md](./file-templates/react-feature-page.md) | `features/<feature>/<Feature>Page.tsx` | 功能页面组件 |
| 3.19 | [react-feature-types.md](./file-templates/react-feature-types.md) | `features/<feature>/types.ts` | 模块类型 |
| 3.20 | [react-engine-index.md](./file-templates/react-engine-index.md) | `features/engine/<engine-module>/index.ts` | Engine 模块入口 |
| 3.21 | [react-engine-types.md](./file-templates/react-engine-types.md) | `features/engine/<engine-module>/types.ts` | Engine 模块类型 |
| 3.22 | [react-engine-api.md](./file-templates/react-engine-api.md) | `features/engine/<engine-module>/api.ts` | Engine API 调用 |
| 3.23 | [react-engine-hook.md](./file-templates/react-engine-hook.md) | `features/engine/<engine-module>/use<Name>.ts` | Engine 自定义 hook |
| 3.24 | [react-engine-context.md](./file-templates/react-engine-context.md) | `features/engine/<engine-module>/<Name>Context.tsx` | Engine 模块级 Context |
| 3.25 | [react-engine-page.md](./file-templates/react-engine-page.md) | `features/engine/<engine-module>/components/<Feature>Page.tsx` | Engine 页面 |

---

## 四、使用说明

### 占位符替换表

| 占位符                | 含义            | 命名规则                             | 示例                                |
| --------------------- | --------------- | ------------------------------------ | ----------------------------------- |
| `<module>`          | Python 功能模块 | snake_case                           | `chunking`, `embeddings`        |
| `<impl>`            | Python 实现文件 | snake_case                           | `mineru_reader`, `chroma_store` |
| `<resource>`        | API 资源名      | snake_case (与 Collection slug 对齐) | `books`, `chunks`               |
| `<concern>`         | 中间件关注点    | snake_case                           | `error_handler`, `cors`         |
| `<verb>_<noun>`     | 脚本名          | snake_case                           | `sync_books`, `build_index`     |
| `<CollectionName>`  | Collection 名   | PascalCase                           | `Books`, `Chunks`               |
| `<collection-slug>` | Collection slug | kebab-case                           | `books`, `chunks`               |
| `<endpoint-name>`   | 端点名          | kebab-case                           | `sync-status`, `batch-embed`    |
| `<lifecycle>`       | 钩子名          | camelCase                            | `afterChange`, `beforeValidate` |
| `<Role>`            | 角色名          | PascalCase                           | `Admin`, `Editor`               |
| `<page>`            | 路由段          | kebab-case                           | `reader`, `chat`                |
| `<feature>`         | 功能模块        | kebab-case                           | `home`, `auth`, `seed`        |
| `<Feature>`         | 功能组件前缀    | PascalCase                           | `Home`, `Auth`, `Seed`        |
| `<ComponentName>`   | 组件名          | PascalCase                           | `BookCard`, `StatusBadge`       |
| `<component-name>`  | UI 原子组件名   | kebab-case                           | `button`, `dialog`              |
| `<Name>`            | 通用名称        | PascalCase                           | `Theme`, `Sidebar`, `Toast`   |
| `<engine-module>`   | Engine 子模块   | kebab-case                           | `books`, `embeddings`           |

### 文件头注释规则

- **Python**: 模块级 docstring，首行为 `"""<name> — <一句话描述>.`
- **TypeScript**: JSDoc 块注释，首行为 `/** <Name> — <一句话描述>.`
- 所有模板均已包含标准注释格式，直接替换占位符即可

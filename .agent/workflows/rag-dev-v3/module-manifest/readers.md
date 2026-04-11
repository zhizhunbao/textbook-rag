# `readers` — 文档阅读 / 解析

```
Layout
文档网格
详情抽屉

UI
文档卡片
封面缩略
状态标签
上传入口

UX
网格浏览
点击详情
PDF 预览
拖拽上传

Func
PDF 读取
MinerU 解析
元数据提取
目录提取
文档上传
文档删除
元数据编辑

Noun
Book
Reader
Pdf
Page
Cover
Author
Toc
Chapter
Upload
Edit
Category
```

```
readers
├── engine_v2/readers/
│   ├── __init__.py                         re-export 公共 API
│   ├── mineru_reader.py                    MinerU PDF 解析器
│   └── cover_extractor.py                  封面图 + 元数据提取
├── engine_v2/api/routes/
│   └── books.py                            书籍 CRUD + 同步端点
├── payload-v2/src/collections/
│   ├── Books.ts                            书籍 Collection
│   └── Chapters.ts                         章节 Collection
├── payload-v2/src/hooks/books/
│   └── afterChange.ts                      书籍变更后触发引擎同步
├── payload-v2/src/features/engine/readers/
│   ├── index.ts                            barrel export
│   ├── types.ts                            LibraryBook · BookCategory 等类型
│   ├── api.ts                              Payload + Engine API 调用
│   ├── useLibraryBooks.ts                  书籍列表 hook (筛选 + 加载)
│   ├── useUpload.ts                        PDF 上传 hook (验证 + 三步上传)
│   └── components/
│       ├── LibraryPage.tsx                 书架页面 (网格 + 表格双视图)
│       ├── BookCard.tsx                    书籍卡片 (封面 + 元数据)
│       ├── BookEditDialog.tsx             元数据编辑表单 (标题/作者/分类)
│       ├── BookPicker.tsx                  选书器 (Chat 入口)
│       ├── BookSelector.tsx                选书下拉 (通用)
│       ├── UploadZone.tsx                 拖拽上传区域
│       └── StatusBadge.tsx                 管线状态徽章
└── payload-v2/src/app/(frontend)/readers/
    ├── page.tsx                            /readers 路由薄壳
    └── [bookId]/
        └── page.tsx                        /readers/:bookId 动态路由
```

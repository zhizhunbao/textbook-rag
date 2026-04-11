# `pdf` — PDF 阅读器

> 跨模块公共模块，从 retrievers/components/ 提取，供 chat、readers 共用。

```
Layout
阅读面板
叠加高亮

UI
页面渲染
页码导航
目录侧栏
缩放控制

UX
滚动翻页
引用跳转
高亮标注
拖拽缩放

Func
PDF 渲染
Bbox 叠加
文本匹配
页面跳转

Noun
Pdf
Viewer
Page
Bbox
Overlay
Zoom
Toc
Highlight
```

```
pdf
└── payload-v2/src/features/shared/pdf/
    ├── index.ts                            barrel export
    ├── PdfViewer.tsx                       PDF 阅读器 (33 KB)             ← 从 retrievers/components/ 迁入
    └── BboxOverlay.tsx                     MinerU bbox 高亮叠加层          ← 从 retrievers/components/ 迁入
```

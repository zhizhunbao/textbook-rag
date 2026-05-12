/* ══════════════════════════════════════════════════════════════
 * 通用模板演示数据 — 覆盖所有 slide type
 * 用于展示模板画廊，不绑定任何具体主题
 * ══════════════════════════════════════════════════════════════ */
const DEMO_SLIDES = [
  /* ── 0: cover — 封面页 ── */
  {
    type: 'cover',
    title: '视频标题占位',
    subtitle: '副标题 · 一句话定位你的内容',
    source: 'https://example.com/source-url',
    _subtitle_text: '这里是字幕区的文字预览',
  },

  /* ── 1: evidence — 数据表格页 (3列 × 3行) ── */
  {
    type: 'evidence',
    title: '数据对比表格',
    table: {
      headers: ['对比项', '方案 A', '方案 B'],
      rows: [
        ['指标一', '**120**', '**89**'],
        ['指标二', '**$2,500**', '**$1,800**'],
        ['指标三', '15 天', '**7 天**'],
      ],
    },
    citation: 'This is an example citation from an official source document.',
    source: 'https://example.com/data-source',
    _subtitle_text: '这是一个三列三行的数据对比表格演示',
  },

  /* ── 2: argument — 论证表格页 ── */
  {
    type: 'argument',
    title: '核心论点展示',
    table: {
      headers: ['类别', '数值'],
      rows: [
        ['基础分', '500'],
        ['附加分', '100'],
        ['特殊加分 — **关键项**', '**600**'],
      ],
    },
    citation: 'Key item: 600 additional points — official policy statement.',
    source: 'https://example.com/argument-source',
    _subtitle_text: '核心论点 两列表格 突出关键数据',
  },

  /* ── 3: evidence — 多列密集表格 (5列 × 3行) ── */
  {
    type: 'evidence',
    title: '密集数据表格 (5列)',
    table: {
      headers: ['编号', '日期', '类型', '数量', '阈值'],
      rows: [
        ['#001', '2026-01', 'A 类', '362', '**742**'],
        ['#002', '2026-02', 'B 类', '264', '**710**'],
        ['#003', '2026-03', 'C 类', '4,000', '**508**'],
      ],
    },
    citation: 'Dense table layout example with 5 columns for compact data display.',
    source: 'https://example.com/dense-table',
    _subtitle_text: '五列紧凑表格布局 自动切换密集模式',
  },

  /* ── 4: argument — 双列对比 ── */
  {
    type: 'argument',
    title: '两种路径对比',
    table: {
      headers: ['你的情况', '推荐路径', '耗时', '费用'],
      rows: [
        ['条件 A', '快速通道', '**约 7 个月**', '**$1,590**'],
        ['条件 B', '标准通道', '**约 13 个月**', '另行查询'],
      ],
    },
    citation: 'Processing time approximately 7 months. Fee: $1,590.',
    source: 'https://example.com/comparison',
    _subtitle_text: '两种路径对比 根据条件选择最优方案',
  },

  /* ── 5: summary — 要点回顾 ── */
  {
    type: 'summary',
    title: '本期要点回顾',
    points: [
      '要点一 = **核心结论**',
      '要点二 = **关键数据**',
      '要点三 = 竞争优势 **264 人**',
      '要点四 = 处理时间 **约 7 个月**',
      '要点五 = 费用 **$1,590 起**',
    ],
    source: 'https://example.com/summary',
    _subtitle_text: '总结一下本期的五个核心要点',
  },

  /* ── 6: cta — 行动号召 ── */
  {
    type: 'cta',
    title: '互动引导标题',
    content: '你觉得哪个方案更适合你？评论区告诉我。',
    source: 'https://example.com/cta',
    _subtitle_text: '评论区互动引导 提升用户参与度',
  },

  /* ── 7: preview — 下期预告 ── */
  {
    type: 'preview',
    title: '下期预告',
    content: '下一期我们聊一个更实际的问题：如何零成本起步',
    source: 'https://example.com/next-episode',
    _subtitle_text: '下期预告 制造期待感 引导关注',
  },
];

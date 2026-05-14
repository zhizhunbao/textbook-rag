/* ═══════════════════════════════════════════════════════════════
 * md-parser.js — Markdown → SlideData[] 解析器
 *
 * 格式规范:
 *   ---                          ← YAML frontmatter 开始
 *   template: competitor-gold
 *   layout: competitor
 *   ---                          ← frontmatter 结束
 *
 *   # 标题                       ← slide 标题 (H1)
 *   > type: cover                ← 元数据 (blockquote)
 *   > subtitle: 副标题
 *   > hook: 600 | 单位 | 说明
 *   > source: https://...
 *   > 字幕: ≤15字
 *
 *   | col1 | col2 |             ← 表格 (标准 markdown)
 *   |------|------|
 *   | a    | b    |
 *
 *   - item1                     ← 列表 (summary 用)
 *   - item2
 *
 *   正文段落                     ← content (cta/preview 用)
 *
 *   ---                          ← slide 分隔符
 * ═══════════════════════════════════════════════════════════════ */

/**
 * 解析 slides.md → { meta: {template, layout}, slides: SlideData[] }
 * @param {string} mdText - 原始 markdown 文本
 * @returns {{ meta: Object, slides: Array }}
 */
function parseSlidesMarkdown(mdText) {
  const result = { meta: {}, slides: [] };
  let text = mdText.replace(/\r\n/g, '\n').trim();

  /* ── 1. 提取 YAML frontmatter ── */
  const fmMatch = text.match(/^---\n([\s\S]*?)\n---/);
  if (fmMatch) {
    for (const line of fmMatch[1].split('\n')) {
      const m = line.match(/^\s*([\w-]+)\s*:\s*(.+)/);
      if (m) result.meta[m[1].trim()] = m[2].trim();
    }
    text = text.slice(fmMatch[0].length).trim();
  }

  /* ── 2. 按 --- 切分 slides ── */
  const blocks = text.split(/\n---(?:\n|$)/);

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const slide = _parseSlideBlock(trimmed, result.slides.length);
    if (slide) result.slides.push(slide);
  }

  return result;
}

/* ── 解析单个 slide 块 ── */
function _parseSlideBlock(block, slideIndex) {
  const lines = block.split('\n');
  const slide = {};
  const tableLines = [];
  const listItems = [];
  const contentLines = [];

  for (const line of lines) {
    const t = line.trim();
    if (!t) continue;

    /* H1 标题 */
    if (t.startsWith('# ') && !slide.title) {
      slide.title = t.replace(/^#+\s*/, '');
      continue;
    }

    /* 元数据 blockquote */
    if (t.startsWith('> ')) {
      const meta = t.replace(/^>\s*/, '');
      const m = meta.match(/^(.+?):\s*([\s\S]+)/);
      if (m) {
        const key = m[1].trim();
        const val = m[2].trim();
        switch (key) {
          case 'type':     slide.type = val; break;
          case 'subtitle': slide.subtitle = val; break;
          case 'source':   slide.source = val; break;
          case '字幕':     slide._subtitle_text = val; break;
          case 'hook': {
            const parts = val.split('|').map(s => s.trim());
            slide.hookNumber = parts[0] || '';
            slide.hookUnit = parts[1] || '';
            slide.hookCaption = parts[2] || '';
            break;
          }
          case 'citation': slide.citation = val; break;
        }
      }
      continue;
    }

    /* 表格行 */
    if (t.startsWith('|')) {
      // 跳过分隔行 |---|---|
      if (/^\|[\s\-:|]+\|$/.test(t)) continue;
      tableLines.push(t);
      continue;
    }

    /* 列表项 */
    if (t.startsWith('- ')) {
      listItems.push(t.replace(/^-\s*/, ''));
      continue;
    }

    /* 其余视为正文 */
    contentLines.push(t);
  }

  /* 组装 table */
  if (tableLines.length > 0) {
    const parseRow = (line) =>
      line.split('|').filter(s => s.trim()).map(s => s.trim());
    slide.table = {
      headers: parseRow(tableLines[0]),
      rows: tableLines.slice(1).map(parseRow),
    };
  }

  /* 组装 points */
  if (listItems.length > 0) {
    slide.points = listItems;
  }

  /* 组装 content */
  if (contentLines.length > 0) {
    slide.content = contentLines.join('\n');
  }

  /* 默认 type 推断 */
  if (!slide.type) {
    if (slideIndex === 0) slide.type = 'cover';
    else if (slide.points) slide.type = 'summary';
    else if (slide.table) slide.type = 'evidence';
    else slide.type = 'argument';
  }

  return slide.title ? slide : null;
}

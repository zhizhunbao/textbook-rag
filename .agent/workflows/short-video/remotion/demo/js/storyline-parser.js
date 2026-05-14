/* ═══════════════════════════════════════════════════════════════
 * storyline-parser.js — storyline.md → SlideData[] 解析器
 *
 * storyline 格式:
 *   # 总标题
 *   > **核心问题：** ...
 *   > **时长：** ...
 *   ---
 *   ## 一、钩子
 *   ### 论点
 *   | col1 | col2 |
 *   |------|------|
 *   ### 证据
 *   > citation
 *   **台词方向：** "..."
 *   ---
 *   ## 十三、总结
 *   ## 十四、互动
 *   ## 十五、下期预告
 *   ---
 *   ## 📋 引用来源汇总 / 引用需求清单
 *
 * 输出: 与 slides.md parser 相同的 { meta, slides: SlideData[] }
 * ═══════════════════════════════════════════════════════════════ */

function parseStorylineMarkdown(mdText) {
  const result = { meta: {}, slides: [] };
  let text = mdText.replace(/\r\n/g, '\n').trim();

  /* ── 1. 提取 H1 标题和 blockquote 元数据 ── */
  const h1Match = text.match(/^# (.+)/m);
  const overallTitle = h1Match ? h1Match[1].trim() : '未命名';

  // 提取顶部 blockquote 元数据
  const metaLines = [];
  for (const line of text.split('\n')) {
    const t = line.trim();
    if (t.startsWith('> ')) {
      const m = t.replace(/^>\s*/, '').replace(/\*\*/g, '');
      const kv = m.match(/^(.+?)[:：]\s*(.+)/);
      if (kv) {
        const key = kv[1].trim();
        const val = kv[2].trim();
        result.meta[key] = val;
        metaLines.push({ key, val });
      }
    } else if (t.startsWith('---') && metaLines.length > 0) {
      break;
    }
  }

  /* 默认模板 */
  if (!result.meta.template) result.meta.template = 'competitor-gold';
  if (!result.meta.layout) result.meta.layout = 'competitor';

  /* ── 2. 按 ## 切分章节 ── */
  const sectionRegex = /^## (.+)/gm;
  const sections = [];
  let match;
  const indices = [];

  while ((match = sectionRegex.exec(text)) !== null) {
    indices.push({ index: match.index, title: match[1].trim() });
  }

  for (let i = 0; i < indices.length; i++) {
    const start = indices[i].index;
    const end = i + 1 < indices.length ? indices[i + 1].index : text.length;
    sections.push({
      rawTitle: indices[i].title,
      body: text.slice(start, end).trim(),
    });
  }

  /* ── 3. 分类并转换每个 section ── */
  // 识别特殊 section
  const isHook = (t) => /钩子|hook/i.test(t);
  const isSummary = (t) => /总结|回顾|要点/i.test(t);
  const isCta = (t) => /互动|收尾|cta/i.test(t);
  const isPreview = (t) => /预告|下期|下集/i.test(t);
  const isReference = (t) => /引用来源|引用需求|引用清单|📋/i.test(t);

  // 生成 cover slide
  const hookSection = sections.find(s => isHook(s.rawTitle));
  const coverSlide = {
    type: 'cover',
    title: _cleanSectionTitle(overallTitle),
    subtitle: result.meta['核心问题'] || result.meta['core'] || '',
    _subtitle_text: _truncate(overallTitle, 15),
  };

  // 从 hook section 提取 hookNumber
  if (hookSection) {
    const table = _extractTable(hookSection.body);
    if (table && table.rows.length > 0) {
      // 找第一个带数字的单元格作为 hook
      for (const row of table.rows) {
        for (const cell of row) {
          const numMatch = cell.replace(/\*\*/g, '').match(/^[\d,.]+/);
          if (numMatch) {
            coverSlide.hookNumber = numMatch[0];
            coverSlide.hookUnit = row[row.length - 1].replace(/\*\*/g, '');
            break;
          }
        }
        if (coverSlide.hookNumber) break;
      }
    }
    // 提取 source
    coverSlide.source = _extractSource(hookSection.body);
  }

  result.slides.push(coverSlide);

  // 处理每个 section
  for (const sec of sections) {
    const title = sec.rawTitle;

    // 跳过引用汇总
    if (isReference(title)) continue;

    if (isHook(title)) {
      // hook 已作为 cover 处理，但如果有表格也生成一页 evidence
      const table = _extractTable(sec.body);
      if (table && table.rows.length > 1) {
        result.slides.push({
          type: 'evidence',
          title: _cleanSectionTitle(title),
          table: table,
          source: _extractSource(sec.body),
          citation: _extractCitation(sec.body),
          _subtitle_text: _extractSubtitle(sec.body, title),
        });
      }
    } else if (isSummary(title)) {
      // 总结页 → summary (用表格的第一列作 points)
      const table = _extractTable(sec.body);
      const points = [];
      if (table) {
        table.rows.forEach(r => {
          if (r.length >= 2) points.push(`${r[0]}: ${r[1]}`);
        });
      }
      if (points.length === 0) {
        // 尝试从列表提取
        const listItems = _extractList(sec.body);
        points.push(...listItems);
      }
      result.slides.push({
        type: 'summary',
        title: '本期要点回顾',
        points: points.length > 0 ? points : ['（无要点）'],
        source: _extractSource(sec.body),
        _subtitle_text: _extractSubtitle(sec.body, '要点回顾'),
      });
    } else if (isCta(title)) {
      const scriptLine = _extractScript(sec.body);
      result.slides.push({
        type: 'cta',
        title: _cleanSectionTitle(title),
        content: scriptLine || '评论区聊聊你的情况',
        source: _extractSource(sec.body),
        _subtitle_text: _truncate(scriptLine || '评论区聊聊', 15),
      });
    } else if (isPreview(title)) {
      const scriptLine = _extractScript(sec.body);
      result.slides.push({
        type: 'preview',
        title: '下期预告',
        content: scriptLine || '敬请期待',
        source: _extractSource(sec.body),
        _subtitle_text: _truncate(scriptLine || '下期更精彩', 15),
      });
    } else {
      // 普通论点 → evidence 或 argument
      const table = _extractTable(sec.body);
      if (!table) continue; // 没表格的 section 跳过

      result.slides.push({
        type: result.slides.length % 2 === 0 ? 'evidence' : 'argument',
        title: _cleanSectionTitle(title),
        table: table,
        source: _extractSource(sec.body),
        citation: _extractCitation(sec.body),
        _subtitle_text: _extractSubtitle(sec.body, title),
      });
    }
  }

  return result;
}

/* ── 工具函数 ── */

function _cleanSectionTitle(raw) {
  // 去掉编号: "一、钩子" → "钩子", "二A、入池门槛——FSW" → "入池门槛 FSW"
  return raw
    .replace(/^[一二三四五六七八九十百千]+[A-Za-z]?[、，.\s]+/, '')
    .replace(/——/g, ' ')
    .replace(/—/g, ' ')
    .trim()
    .slice(0, 12); // 标题 ≤12 字
}

function _truncate(text, max) {
  const clean = text.replace(/\*\*/g, '').trim();
  return clean.length > max ? clean.slice(0, max) : clean;
}

function _extractTable(body) {
  const lines = body.split('\n');
  const tableLines = [];
  for (const line of lines) {
    const t = line.trim();
    if (t.startsWith('|')) {
      if (/^\|[\s\-:|]+\|$/.test(t)) continue; // 跳过分隔行
      tableLines.push(t);
    }
  }
  if (tableLines.length < 2) return null; // 至少 header + 1 row

  const parseRow = (line) =>
    line.split('|').filter(s => s.trim()).map(s => s.trim());

  return {
    headers: parseRow(tableLines[0]),
    rows: tableLines.slice(1).map(parseRow),
  };
}

function _extractCitation(body) {
  // 匹配 > "text" 或 > 'text' 格式的引用
  const m = body.match(/^>\s*"(.+?)"/m) || body.match(/^>\s*「(.+?)」/m);
  return m ? m[1] : null;
}

function _extractSource(body) {
  // 从引用或链接中提取 URL
  const urlMatch = body.match(/https?:\/\/[^\s)>\]]+/);
  return urlMatch ? urlMatch[0] : null;
}

function _extractScript(body) {
  // 提取 **台词方向：** 后面的内容
  const m = body.match(/\*\*台词方向[：:]\*\*\s*[""]?(.+?)[""]?\s*$/m);
  if (m) return m[1].replace(/^[""]|[""]$/g, '').trim();
  // 回退: 取第一个非标题、非元数据的文本行
  for (const line of body.split('\n')) {
    const t = line.trim();
    if (!t || t.startsWith('#') || t.startsWith('>') || t.startsWith('|') || t.startsWith('-') || t.startsWith('*')) continue;
    return t;
  }
  return null;
}

function _extractList(body) {
  const items = [];
  for (const line of body.split('\n')) {
    const t = line.trim();
    if (t.startsWith('- ')) items.push(t.replace(/^-\s*/, ''));
  }
  return items;
}

function _extractSubtitle(body, fallback) {
  const script = _extractScript(body);
  if (script) return _truncate(script, 15);
  return _truncate(fallback, 15);
}

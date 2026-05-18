import React from 'react';
import { theme, baseStyles } from '../theme';
import type { SlideData } from '../types';

/**
 * 通用内容页 — 全部居中，上下摞起来
 *
 * 布局:
 * ┌──────────────────────────────────┐
 * │                                  │
 * │            标题 (居中)             │
 * │          表格/内容 (居中)           │
 * │            引用 (居中)             │
 * │          来源URL (居中底部)         │
 * │                                  │
 * └──────────────────────────────────┘
 */
export const ContentSlide: React.FC<{ slide: SlideData }> = ({ slide }) => {
  const isCta = slide.type === 'cta' || slide.type === 'preview';

  // 估算表格是否高到需要顶部对齐（占用 >50% 可用空间）
  const isLargeTable = slide.table && slide.table.rows.length >= 5;

  return (
    <div style={{
      ...baseStyles.slideArea,
      justifyContent: isLargeTable ? 'flex-start' : 'center',
    }}>
      {/* 标题 */}
      <h2 style={baseStyles.heading}>{slide.title}</h2>

      {/* 内容区 — 居中堆叠 */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        {/* 表格 */}
        {slide.table && <DataTable headers={slide.table.headers} rows={slide.table.rows} />}

        {/* 列表要点 */}
        {slide.points && (
          <ul style={{
            fontSize: 38, lineHeight: 2, color: theme.textSecondary,
            margin: 0, padding: 0, listStyle: 'none',
            textAlign: 'center',
          }}>
            {slide.points.map((p, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                <span dangerouslySetInnerHTML={{ __html: boldToAccent(p) }} />
              </li>
            ))}
          </ul>
        )}

        {/* CTA / Preview 正文 */}
        {slide.content && (
          <p style={{
            fontSize: isCta ? 48 : 42,
            lineHeight: 1.7,
            color: isCta ? theme.accentLight : theme.textSecondary,
            fontWeight: isCta ? 700 : 400,
            margin: 0,
            textAlign: 'center',
          }}>
            <span dangerouslySetInnerHTML={{ __html: boldToAccent(slide.content) }} />
          </p>
        )}
      </div>

      {/* 引用 */}
      {slide.citation && (
        <div style={{
          borderLeft: `4px solid ${theme.citationBorder}`,
          background: theme.citationBg,
          padding: '14px 24px',
          borderRadius: '0 8px 8px 0',
          color: theme.citationText,
          fontSize: 28, lineHeight: 1.6,
          fontStyle: 'italic',
          marginTop: 16,
          textAlign: 'center',
          maxWidth: '90%',
        }}>
          {slide.citation}
        </div>
      )}
    </div>
  );
};

/* ── 表格 ── */
const DataTable: React.FC<{ headers: string[]; rows: string[][] }> = ({ headers, rows }) => {
  const colCount = headers.length;
  const rowCount = rows.length;

  // ── 自适应密度：从最大字号开始试，放不下就降级 ──
  // slide 832px - padding 60+24 - title ~95px = ~650px 可用
  const AVAILABLE_H = 650;
  const TABLE_W = 1760; // 1920 - 80*2 padding

  const densityLevels = [
    { padV: 16, padH: 28, fsBody: 36, fsHead: 32, name: 'normal' },
    { padV: 10, padH: 18, fsBody: 34, fsHead: 30, name: 'dense' },
    { padV: 6,  padH: 12, fsBody: 30, fsHead: 26, name: 'xDense' },
    { padV: 4,  padH: 10, fsBody: 26, fsHead: 22, name: 'xxDense' },
    { padV: 2,  padH: 8,  fsBody: 22, fsHead: 20, name: 'xxxDense' },
  ];

  /** 估算一个单元格在给定字号下占几行 */
  const estimateCellLines = (text: string, fs: number, cw: number): number => {
    if (!text) return 1;
    const cjk = (text.match(/[\u4e00-\u9fff\uff00-\uffef]/g) || []).length;
    const other = text.length - cjk;
    // CJK 字宽 ≈ 字号，Latin/数字 ≈ 0.55 × 字号
    const textWidth = cjk * fs + other * fs * 0.55;
    const usable = cw - 20; // 留 padding
    return Math.max(1, Math.ceil(textWidth / Math.max(usable, 60)));
  };

  /** 估算整个表格在给定密度下的总高度 */
  const estimateHeight = (level: typeof densityLevels[0]): number => {
    const cw = TABLE_W / colCount;
    // header 行
    let h = level.fsHead * 1.5 + level.padV * 2 + 2; // +2 border
    // data 行
    for (const row of rows) {
      const maxLines = Math.max(...row.map(cell => estimateCellLines(cell, level.fsBody, cw)));
      h += level.fsBody * 1.5 * maxLines + level.padV * 2 + 1; // +1 border
    }
    return h;
  };

  // 选最大的能放下的等级
  let chosen = densityLevels[densityLevels.length - 1]; // 兜底 xxDense
  for (const level of densityLevels) {
    if (estimateHeight(level) <= AVAILABLE_H) {
      chosen = level;
      break;
    }
  }

  const pad = `${chosen.padV}px ${chosen.padH}px`;
  const fsBody = chosen.fsBody;
  const fsHead = chosen.fsHead;

  // 自动检测哪些列包含 URL（用于特殊样式）
  const isUrlCol: boolean[] = headers.map((h, ci) => {
    if (/链接|url|link|来源|source/i.test(h)) return true;
    return rows.some(r => r[ci] && /^https?:\/\//.test(r[ci]));
  });
  const hasUrlCols = isUrlCol.some(Boolean);

  // 计算列宽百分比：URL 列分配更多空间
  const colWidths: string[] = (() => {
    if (!hasUrlCols) return headers.map(() => `${100 / colCount}%`);
    const urlCount = isUrlCol.filter(Boolean).length;
    const normalCount = colCount - urlCount;
    // URL 列占总宽的 45%（多个则均分），其余列均分剩余
    const urlTotalPct = Math.min(55, 45 * urlCount);
    const normalTotalPct = 100 - urlTotalPct;
    return isUrlCol.map(isUrl =>
      isUrl
        ? `${urlTotalPct / urlCount}%`
        : `${normalCount > 0 ? normalTotalPct / normalCount : 100 / colCount}%`,
    );
  })();

  return (
    <table style={{
      width: '100%',
      borderCollapse: 'collapse',
      tableLayout: 'fixed',
    }}>
      <colgroup>
        {colWidths.map((w, i) => (
          <col key={i} style={{ width: w }} />
        ))}
      </colgroup>
      <thead>
        <tr>
          {headers.map((h, i) => (
            <th key={i} style={{
              background: theme.tableHeaderBg,
              color: theme.tableHeaderText,
              padding: pad, fontSize: fsHead,
              fontWeight: 700,
              textAlign: isUrlCol[i] ? 'left' : 'center',
              borderBottom: `2px solid ${theme.tableBorder}`,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              <span dangerouslySetInnerHTML={{ __html: boldToAccent(h) }} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, ri) => (
          <tr key={ri}>
            {row.map((cell, ci) => {
              const cellIsUrl = isUrlCol[ci] || /^https?:\/\//.test(cell);
              return (
                <td key={ci} style={{
                  color: theme.textSecondary,
                  padding: pad,
                  fontSize: cellIsUrl ? Math.max(18, fsBody - 4) : fsBody,
                  textAlign: cellIsUrl ? 'left' : 'center',
                  borderBottom: ri < rows.length - 1
                    ? `1px solid ${theme.tableBorder}`
                    : 'none',
                  wordBreak: cellIsUrl ? 'break-all' : 'normal',
                  overflowWrap: 'break-word',
                  lineHeight: cellIsUrl ? 1.3 : 1.5,
                }}>
                  <span dangerouslySetInnerHTML={{ __html: boldToAccent(cell) }} />
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

/** **text** → 金色加粗 */
function boldToAccent(text: string): string {
  return text.replace(
    /\*\*(.+?)\*\*/g,
    `<strong style="color:${theme.accentLight};font-weight:800">$1</strong>`,
  );
}

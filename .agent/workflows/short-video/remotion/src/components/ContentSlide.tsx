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

  return (
    <div style={baseStyles.slideArea}>
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

      {/* 来源 URL — 右上角水印 */}
      {slide.source && (
        <div style={{
          position: 'absolute', top: 20, right: 30,
          fontSize: 24,
          color: theme.sourceText,
          fontFamily: "'Inter', monospace",
        }}>
          {slide.source}
        </div>
      )}
    </div>
  );
};

/* ── 表格 ── */
const DataTable: React.FC<{ headers: string[]; rows: string[][] }> = ({ headers, rows }) => {
  const colCount = headers.length;
  const rowCount = rows.length;

  // 密度等级: 列×行越多，字越小、间距越紧
  // slide 区域 880px，标题占 ~84px，可用 ~712px
  const isXXDense = rowCount >= 8;  // 8+ 行：超密集，防溢出
  const isXDense = colCount >= 6 || (colCount >= 5 && rowCount >= 5);
  const isDense  = colCount >= 4 || rowCount > 4;

  const pad = isXXDense ? '4px 10px' : isXDense ? '8px 14px' : isDense ? '10px 18px' : '16px 28px';
  const fsBody = isXXDense ? 24 : isXDense ? 30 : isDense ? 34 : 36;
  const fsHead = isXXDense ? 22 : isXDense ? 26 : isDense ? 30 : 32;

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

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
            fontSize: 32, lineHeight: 2, color: theme.textSecondary,
            margin: 0, padding: 0, listStyle: 'none',
            textAlign: 'center',
          }}>
            {slide.points.map((p, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                <span dangerouslySetInnerHTML={{ __html: boldToBlue(p) }} />
              </li>
            ))}
          </ul>
        )}

        {/* CTA / Preview 正文 */}
        {slide.content && (
          <p style={{
            fontSize: isCta ? 42 : 36,
            lineHeight: 1.7,
            color: isCta ? theme.blueLight : theme.textSecondary,
            fontWeight: isCta ? 700 : 400,
            margin: 0,
            textAlign: 'center',
          }}>
            <span dangerouslySetInnerHTML={{ __html: boldToBlue(slide.content) }} />
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
          fontSize: 24, lineHeight: 1.6,
          fontStyle: 'italic',
          marginTop: 16,
          textAlign: 'center',
          maxWidth: '90%',
        }}>
          {slide.citation}
        </div>
      )}

      {/* 来源 URL — 显示完整，放在最底部 */}
      {slide.source && (
        <div style={{
          fontSize: 18,
          color: 'rgba(255, 255, 255, 0.35)',
          marginTop: 12,
          textAlign: 'center',
          wordBreak: 'break-all' as const,
          maxWidth: '90%',
          lineHeight: 1.4,
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
  const dense = rows.length > 4 || headers.length > 4;
  const pad = dense ? '12px 20px' : '16px 28px';
  const fs = dense ? 26 : 30;

  return (
    <table style={{
      width: '100%',
      borderCollapse: 'separate',
      borderSpacing: '0 6px',
    }}>
      <thead>
        <tr>
          {headers.map((h, i) => (
            <th key={i} style={{
              background: theme.tableHeaderBg,
              color: theme.tableHeaderText,
              padding: pad, fontSize: dense ? 22 : 26,
              fontWeight: 700, textAlign: 'center',
              ...(i === 0 ? { borderRadius: '8px 0 0 8px' } : {}),
              ...(i === headers.length - 1 ? { borderRadius: '0 8px 8px 0' } : {}),
            }}>
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, ri) => (
          <tr key={ri}>
            {row.map((cell, ci) => (
              <td key={ci} style={{
                background: ri % 2 === 0 ? theme.tableRowOdd : theme.tableRowEven,
                color: theme.textSecondary,
                padding: pad, fontSize: fs,
                textAlign: 'center',
                ...(ci === 0 ? { borderRadius: '6px 0 0 6px' } : {}),
                ...(ci === row.length - 1 ? { borderRadius: '0 6px 6px 0' } : {}),
              }}>
                <span dangerouslySetInnerHTML={{ __html: boldToBlue(cell) }} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

/** **text** → 蓝色加粗 */
function boldToBlue(text: string): string {
  return text.replace(
    /\*\*(.+?)\*\*/g,
    `<strong style="color:${theme.blueLight};font-weight:800">$1</strong>`,
  );
}

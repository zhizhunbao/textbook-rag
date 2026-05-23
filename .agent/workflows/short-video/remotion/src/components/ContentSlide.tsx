import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';
import type { SlideData } from '../types';

/**
 * 通用内容页 — 带入场动画
 *
 * 动画:
 *   标题: 从上方滑入 + fade in (200ms)
 *   表格行: 逐行从下方弹入 (每行延迟 100ms)
 *   引用块: 从左侧滑入 + fade in
 *   列表要点: 逐条弹入
 */
export const ContentSlide: React.FC<{ slide: SlideData; theme: ThemeConfig }> = ({ slide, theme: t }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const styles = getBaseStyles(t);

  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const hasTable = !!slide.table;

  // ── 标题动画 ──
  const titleY = interpolate(frame, [0, 12], [-20, 0], { extrapolateRight: 'clamp' });
  const titleOpacity = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp' });

  // ── 引用块动画 ──
  const citationX = interpolate(frame, [8, 22], [-30, 0], { extrapolateRight: 'clamp' });
  const citationOpacity = interpolate(frame, [8, 22], [0, 1], { extrapolateRight: 'clamp' });

  // ── CTA 内容动画 ──
  const contentOpacity = interpolate(frame, [5, 18], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame: Math.max(0, frame - 5), fps, config: { damping: 15, stiffness: 80 } });

  return (
    <div style={{
      ...styles.slideArea,
      justifyContent: hasTable ? 'flex-start' : 'center',
    }}>
      {/* 有表格: 标题固定在顶部 */}
      {hasTable && (
        <h2 style={{
          ...styles.heading,
          transform: `translateY(${titleY}px)`,
          opacity: titleOpacity,
        }}>
          {slide.title}
        </h2>
      )}

      {/* 内容区 */}
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        ...(hasTable ? { flex: 1 } : {}),
      }}>
        {/* 无表格: 标题和内容作为一组居中 */}
        {!hasTable && (
          <h2 style={{
            ...styles.heading,
            transform: `translateY(${titleY}px)`,
            opacity: titleOpacity,
          }}>
            {slide.title}
          </h2>
        )}

        {/* 表格 — 带逐行入场动画 */}
        {slide.table && <DataTable headers={slide.table.headers} rows={slide.table.rows} theme={t} />}

        {/* 列表要点 — 逐条弹入 */}
        {slide.points && (
          <ul style={{
            fontSize: 38, lineHeight: 2, color: t.textSecondary,
            margin: 0, padding: 0, listStyle: 'none',
            textAlign: 'center',
          }}>
            {slide.points.map((p, i) => {
              const delay = 8 + i * 4;
              const pointOpacity = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: 'clamp' });
              const pointY = interpolate(frame, [delay, delay + 10], [15, 0], { extrapolateRight: 'clamp' });
              return (
                <li key={i} style={{
                  marginBottom: 4,
                  opacity: pointOpacity,
                  transform: `translateY(${pointY}px)`,
                }}>
                  <span dangerouslySetInnerHTML={{ __html: boldToAccent(p, t) }} />
                </li>
              );
            })}
          </ul>
        )}

        {/* CTA / Preview 正文 — 缩放弹入 */}
        {slide.content && (
          <p style={{
            fontSize: isCta ? 48 : 42,
            lineHeight: 1.7,
            color: isCta ? t.accentLight : t.textSecondary,
            fontWeight: isCta ? 700 : 400,
            margin: 0,
            textAlign: 'center',
            opacity: contentOpacity,
            transform: `scale(${contentScale})`,
          }}>
            <span dangerouslySetInnerHTML={{ __html: boldToAccent(slide.content, t) }} />
          </p>
        )}
      </div>

      {/* 引用 — 从左侧滑入 */}
      {slide.citation && (
        <div style={{
          borderLeft: `4px solid ${t.citationBorder}`,
          background: t.citationBg,
          padding: '14px 24px',
          borderRadius: '0 8px 8px 0',
          color: t.citationText,
          fontSize: 28, lineHeight: 1.6,
          fontStyle: 'italic',
          marginTop: 16,
          textAlign: 'center',
          maxWidth: '90%',
          transform: `translateX(${citationX}px)`,
          opacity: citationOpacity,
        }}>
          {slide.citation}
        </div>
      )}
    </div>
  );
};

/* ── 表格 — 带逐行入场动画 ── */
const DataTable: React.FC<{ headers: string[]; rows: string[][]; theme: ThemeConfig }> = ({ headers, rows, theme: t }) => {
  const frame = useCurrentFrame();
  const colCount = headers.length;
  const rowCount = rows.length;

  const AVAILABLE_H = 650;
  const TABLE_W = 1760;

  const densityLevels = [
    { padV: 16, padH: 28, fsBody: 36, fsHead: 32, name: 'normal' },
    { padV: 10, padH: 18, fsBody: 34, fsHead: 30, name: 'dense' },
    { padV: 6,  padH: 12, fsBody: 30, fsHead: 26, name: 'xDense' },
    { padV: 4,  padH: 10, fsBody: 26, fsHead: 22, name: 'xxDense' },
    { padV: 2,  padH: 8,  fsBody: 22, fsHead: 20, name: 'xxxDense' },
  ];

  const estimateCellLines = (text: string, fs: number, cw: number): number => {
    if (!text) return 1;
    const cjk = (text.match(/[\u4e00-\u9fff\uff00-\uffef]/g) || []).length;
    const other = text.length - cjk;
    const textWidth = cjk * fs + other * fs * 0.55;
    const usable = cw - 20;
    return Math.max(1, Math.ceil(textWidth / Math.max(usable, 60)));
  };

  const estimateHeight = (level: typeof densityLevels[0]): number => {
    const cw = TABLE_W / colCount;
    let h = level.fsHead * 1.5 + level.padV * 2 + 2;
    for (const row of rows) {
      const maxLines = Math.max(...row.map(cell => estimateCellLines(cell, level.fsBody, cw)));
      h += level.fsBody * 1.5 * maxLines + level.padV * 2 + 1;
    }
    return h;
  };

  let chosen = densityLevels[densityLevels.length - 1];
  for (const level of densityLevels) {
    if (estimateHeight(level) <= AVAILABLE_H) {
      chosen = level;
      break;
    }
  }

  const pad = `${chosen.padV}px ${chosen.padH}px`;
  const fsBody = chosen.fsBody;
  const fsHead = chosen.fsHead;

  const isUrlCol: boolean[] = headers.map((h, ci) => {
    if (/链接|url|link|来源|source/i.test(h)) return true;
    return rows.some(r => r[ci] && /^https?:\/\//.test(r[ci]));
  });
  const hasUrlCols = isUrlCol.some(Boolean);

  const colWidths: string[] = (() => {
    if (!hasUrlCols) return headers.map(() => `${100 / colCount}%`);
    const urlCount = isUrlCol.filter(Boolean).length;
    const normalCount = colCount - urlCount;
    const urlTotalPct = Math.min(55, 45 * urlCount);
    const normalTotalPct = 100 - urlTotalPct;
    return isUrlCol.map(isUrl =>
      isUrl
        ? `${urlTotalPct / urlCount}%`
        : `${normalCount > 0 ? normalTotalPct / normalCount : 100 / colCount}%`,
    );
  })();

  // ── 表头动画 ──
  const headerOpacity = interpolate(frame, [5, 15], [0, 1], { extrapolateRight: 'clamp' });

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
        <tr style={{ opacity: headerOpacity }}>
          {headers.map((h, i) => (
            <th key={i} style={{
              background: t.tableHeaderBg,
              color: t.tableHeaderText,
              padding: pad, fontSize: fsHead,
              fontWeight: 700,
              textAlign: isUrlCol[i] ? 'left' : 'center',
              borderBottom: `2px solid ${t.tableBorder}`,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              <span dangerouslySetInnerHTML={{ __html: boldToAccent(h, t) }} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, ri) => {
          // 逐行入场动画：每行延迟 3 帧
          const rowDelay = 10 + ri * 3;
          const rowOpacity = interpolate(frame, [rowDelay, rowDelay + 8], [0, 1], { extrapolateRight: 'clamp' });
          const rowY = interpolate(frame, [rowDelay, rowDelay + 8], [12, 0], { extrapolateRight: 'clamp' });

          return (
            <tr key={ri} style={{
              opacity: rowOpacity,
              transform: `translateY(${rowY}px)`,
            }}>
              {row.map((cell, ci) => {
                const cellIsUrl = isUrlCol[ci] || /^https?:\/\//.test(cell);
                return (
                  <td key={ci} style={{
                    color: t.textSecondary,
                    padding: pad,
                    fontSize: cellIsUrl ? Math.max(18, fsBody - 4) : fsBody,
                    textAlign: cellIsUrl ? 'left' : 'center',
                    borderBottom: ri < rows.length - 1
                      ? `1px solid ${t.tableBorder}`
                      : 'none',
                    wordBreak: cellIsUrl ? 'break-all' : 'normal',
                    overflowWrap: 'break-word',
                    lineHeight: cellIsUrl ? 1.3 : 1.5,
                  }}>
                    <span dangerouslySetInnerHTML={{ __html: boldToAccent(cell, t) }} />
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
};

/** **text** → 强调色加粗 */
function boldToAccent(text: string, t: ThemeConfig): string {
  return text.replace(
    /\*\*(.+?)\*\*/g,
    `<strong style="color:${t.accentLight};font-weight:800">$1</strong>`,
  );
}

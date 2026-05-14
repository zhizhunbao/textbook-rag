/* ═══════════════════════════════════════════════════════════════
 * render-utils.js — 渲染通用工具函数
 * 职责: 表格/列表/引用/来源等 HTML 片段生成
 * 被所有 layouts/*.js 依赖
 * ═══════════════════════════════════════════════════════════════ */

/* ── **text** → <strong> 高亮 ── */
function tplBold(text, color) {
  return text.replace(/\*\*(.+?)\*\*/g, `<strong style="color:${color};font-weight:800">$1</strong>`);
}

/* ── 来源 URL ── */
function tplSource(src, p, align) {
  if (!src) return '';
  return `<div style="font-size:16px;color:${p.sourceText};margin-top:16px;text-align:${align || 'center'};word-break:break-all;max-width:90%;line-height:1.4;font-family:'Inter',monospace">${src}</div>`;
}

/* ── 引用块 ── */
function tplCitation(cit, p, align) {
  if (!cit) return '';
  return `<div style="border-left:4px solid ${p.citationBorder};background:${p.citationBg};padding:12px 20px;border-radius:0 8px 8px 0;color:${p.citationText};font-size:22px;line-height:1.6;font-style:italic;margin-top:14px;text-align:${align || 'center'};max-width:95%">${cit}</div>`;
}

/* ── 表格 HTML ── */
function tplTableHTML(table, p, dense) {
  const pad = dense ? '10px 16px' : '14px 24px';
  const thFs = dense ? 20 : 24;
  const tdFs = dense ? 24 : 28;
  let h = '<table style="width:100%;border-collapse:separate;border-spacing:0 5px;table-layout:fixed"><thead><tr>';
  table.headers.forEach((hd, i) => {
    const br = i === 0 ? 'border-radius:8px 0 0 8px;' : i === table.headers.length - 1 ? 'border-radius:0 8px 8px 0;' : '';
    h += `<th style="background:${p.tableHeaderBg};color:${p.tableHeaderText};padding:${pad};font-size:${thFs}px;font-weight:700;text-align:center;${br}">${hd}</th>`;
  });
  h += '</tr></thead><tbody>';
  table.rows.forEach((row, ri) => {
    h += '<tr>';
    row.forEach((cell, ci) => {
      const bg = ri % 2 === 0 ? p.tableRowOdd : p.tableRowEven;
      const br = ci === 0 ? 'border-radius:6px 0 0 6px;' : ci === row.length - 1 ? 'border-radius:0 6px 6px 0;' : '';
      h += `<td style="background:${bg};color:${p.textSecondary};padding:${pad};font-size:${tdFs}px;text-align:center;${br}">${tplBold(cell, p.accentLight)}</td>`;
    });
    h += '</tr>';
  });
  h += '</tbody></table>';
  return h;
}

/* ── 列表 ── */
function tplPoints(points, p, align, fs) {
  let h = `<ul style="font-size:${fs || 30}px;line-height:2;color:${p.textSecondary};margin:0;padding:0;list-style:none;text-align:${align || 'center'}">`;
  points.forEach(pt => { h += `<li>${tplBold(pt, p.accentLight)}</li>`; });
  h += '</ul>';
  return h;
}

/* ── 正文内容 ── */
function tplContent(slide, p, align, isCta) {
  if (!slide.content) return '';
  const fs = isCta ? 40 : 34;
  const clr = isCta ? p.accentLight : p.textSecondary;
  const fw = isCta ? 700 : 400;
  return `<p style="font-size:${fs}px;line-height:1.7;color:${clr};font-weight:${fw};margin:0;text-align:${align || 'center'}">${tplBold(slide.content, p.accentLight)}</p>`;
}

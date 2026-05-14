/* ═══════════════════════════════════════════════════════════════
 * competitor.js — 竞品金布局 (数据优先 + 金色强调)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_competitor(slide, p) {
  let h = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  if (slide.hookNumber) {
    h += `<div style="font-size:120px;font-weight:900;color:${p.accent};line-height:1;margin-bottom:8px;text-shadow:0 0 60px ${p.accent}40">${slide.hookNumber}</div>`;
    if (slide.hookUnit) h += `<div style="font-size:28px;color:${p.accentLight};font-weight:600;letter-spacing:3px;margin-bottom:16px">${slide.hookUnit}</div>`;
    if (slide.hookCaption) h += `<div style="font-size:20px;color:${p.accentMuted};font-weight:400;margin-bottom:36px">${slide.hookCaption}</div>`;
  }
  h += `<h1 style="font-size:72px;font-weight:800;color:${p.textPrimary};letter-spacing:1px;line-height:1.15;margin:0;text-align:center">${slide.title}</h1>`;
  if (slide.subtitle) h += `<p style="font-size:28px;color:${p.accentLight};font-weight:400;margin-top:20px;letter-spacing:1px;text-align:center">${slide.subtitle}</p>`;
  h += '</div>';
  return h;
}

function renderContent_competitor(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = '<div style="width:100%;display:flex;flex-direction:column;align-items:center">';
  h += `<h2 style="font-size:48px;font-weight:800;color:${p.textPrimary};margin:0 0 28px;text-align:center">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += '</div>';
  return h;
}

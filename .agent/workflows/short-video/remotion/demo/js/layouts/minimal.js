/* ═══════════════════════════════════════════════════════════════
 * minimal.js — 极简水墨布局 (竖线分割 + 左对齐)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_minimal(slide, p) {
  let h = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  h += `<div style="width:12px;height:12px;background:${p.accent};border-radius:50%;margin-bottom:40px"></div>`;
  h += `<h1 style="font-size:80px;font-weight:300;color:${p.textPrimary};letter-spacing:6px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:60px;height:1px;background:${p.accentMuted};margin:32px 0"></div>`;
  if (slide.subtitle) h += `<p style="font-size:24px;color:${p.accentMuted};font-weight:300;letter-spacing:4px;margin:0;text-align:center">${slide.subtitle}</p>`;
  h += '</div>';
  return h;
}

function renderContent_minimal(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = '<div style="width:100%;display:flex;flex-direction:row;gap:40px">';
  h += `<div style="display:flex;flex-direction:column;align-items:center;padding-top:8px"><div style="width:8px;height:8px;background:${p.accent};border-radius:50%;flex-shrink:0"></div><div style="width:1px;flex:1;background:${p.accentMuted}40;margin-top:8px"></div></div>`;
  h += '<div style="flex:1;display:flex;flex-direction:column;align-items:flex-start">';
  h += `<h2 style="font-size:46px;font-weight:300;color:${p.textPrimary};margin:0 0 28px;text-align:left;letter-spacing:2px">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'left', 28);
  if (slide.content) h += tplContent(slide, p, 'left', isCta);
  h += tplCitation(slide.citation, p, 'left');
  h += '</div></div>';
  return h;
}

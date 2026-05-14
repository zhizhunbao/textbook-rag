/* ═══════════════════════════════════════════════════════════════
 * ember.js — 烬火流光布局 (左对齐社论风)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_ember(slide, p) {
  let h = '<div style="display:flex;flex-direction:column;align-items:flex-start;justify-content:center;width:100%;padding-left:40px">';
  h += `<div style="width:120px;height:3px;background:linear-gradient(90deg,${p.accent},${p.accentSecondary});border-radius:2px;margin-bottom:36px"></div>`;
  h += `<h1 style="font-size:72px;font-weight:800;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:left;text-shadow:0 4px 30px ${p.accent}30">${slide.title}</h1>`;
  h += `<div style="display:flex;align-items:center;gap:16px;margin:28px 0"><div style="width:80px;height:1px;background:${p.accentSecondary}"></div><div style="width:10px;height:10px;background:${p.accent};transform:rotate(45deg)"></div><div style="width:80px;height:1px;background:${p.accentSecondary}"></div></div>`;
  if (slide.subtitle) h += `<p style="font-size:28px;color:${p.accentSecondary};font-weight:400;letter-spacing:2px;margin:0;text-align:left">${slide.subtitle}</p>`;
  h += '</div>';
  return h;
}

function renderContent_ember(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = `<div style="width:100%;display:flex;flex-direction:column;align-items:flex-start;border-left:3px solid;border-image:linear-gradient(180deg,${p.accent},${p.accentSecondary}) 1;padding-left:36px">`;
  h += `<h2 style="font-size:48px;font-weight:800;color:${p.textPrimary};margin:0 0 24px;text-align:left">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'left', 28);
  if (slide.content) h += tplContent(slide, p, 'left', isCta);
  h += tplCitation(slide.citation, p, 'left') + '</div>';
  return h;
}

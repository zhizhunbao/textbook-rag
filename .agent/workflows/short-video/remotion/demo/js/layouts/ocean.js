/* ═══════════════════════════════════════════════════════════════
 * ocean.js — 深海蔚蓝布局 (顶栏标题 + 内容区分离)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_ocean(slide, p) {
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  h += `<div style="position:absolute;top:-30px;width:600px;height:3px;background:linear-gradient(90deg,transparent,${p.accent}60,transparent);border-radius:2px"></div>`;
  h += `<div style="position:absolute;top:-18px;width:400px;height:2px;background:linear-gradient(90deg,transparent,${p.accentSecondary}40,transparent);border-radius:2px"></div>`;
  h += `<h1 style="font-size:70px;font-weight:700;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:2px;height:40px;background:linear-gradient(180deg,${p.accent},transparent);margin:20px 0"></div>`;
  if (slide.subtitle) h += `<p style="font-size:30px;color:${p.accentLight};font-weight:400;letter-spacing:1px;margin:0;text-align:center">${slide.subtitle}</p>`;
  h += '</div>';
  return h;
}

function renderContent_ocean(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = '<div style="width:100%;display:flex;flex-direction:column;align-items:center">';
  h += `<div style="width:100%;padding-bottom:16px;margin-bottom:20px;border-bottom:2px solid;border-image:linear-gradient(90deg,transparent,${p.accent},transparent) 1;text-align:center">`;
  h += `<h2 style="font-size:48px;font-weight:700;color:${p.textPrimary};margin:0">${slide.title}</h2></div>`;
  h += '<div style="width:100%;display:flex;flex-direction:column;align-items:center">';
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += '</div>';
  h += `<div style="width:100%;margin-top:16px;padding-top:12px;border-top:1px solid ${p.accent}20;display:flex;flex-direction:column;align-items:center">`;
  h += tplCitation(slide.citation, p, 'center') + '</div></div>';
  return h;
}

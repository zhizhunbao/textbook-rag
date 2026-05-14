/* ═══════════════════════════════════════════════════════════════
 * neon.js — 霓虹脉冲布局 (居中堆叠 + 四角标记)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_neon(slide, p) {
  const glow = `0 0 40px ${p.accent}40, 0 0 80px ${p.accent}20`;
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  h += `<div style="position:absolute;top:-20px;left:-40px;width:60px;height:60px;border-top:2px solid ${p.accent};border-left:2px solid ${p.accent}"></div>`;
  h += `<div style="position:absolute;top:-20px;right:-40px;width:60px;height:60px;border-top:2px solid ${p.accentSecondary};border-right:2px solid ${p.accentSecondary}"></div>`;
  h += `<div style="position:absolute;bottom:-20px;left:-40px;width:60px;height:60px;border-bottom:2px solid ${p.accentSecondary};border-left:2px solid ${p.accentSecondary}"></div>`;
  h += `<div style="position:absolute;bottom:-20px;right:-40px;width:60px;height:60px;border-bottom:2px solid ${p.accent};border-right:2px solid ${p.accent}"></div>`;
  h += `<h1 style="font-size:76px;font-weight:900;color:${p.textPrimary};text-shadow:${glow};letter-spacing:2px;line-height:1.15;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:400px;height:2px;margin:24px 0;background:linear-gradient(90deg,transparent,${p.accent},${p.accentSecondary},transparent)"></div>`;
  if (slide.subtitle) h += `<p style="font-size:26px;color:${p.accentLight};font-weight:400;letter-spacing:3px;text-transform:uppercase;margin:0">${slide.subtitle}</p>`;
  h += '</div>';
  return h;
}

function renderContent_neon(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = `<div style="position:relative;border:1px solid ${p.accent}25;border-radius:4px;padding:12px;width:100%;display:flex;flex-direction:column;align-items:center">`;
  h += `<div style="position:absolute;top:-1px;left:-1px;width:20px;height:20px;border-top:2px solid ${p.accent};border-left:2px solid ${p.accent}"></div>`;
  h += `<div style="position:absolute;top:-1px;right:-1px;width:20px;height:20px;border-top:2px solid ${p.accent};border-right:2px solid ${p.accent}"></div>`;
  h += `<h2 style="font-size:48px;font-weight:900;color:${p.textPrimary};margin:0 0 24px;text-align:center;text-shadow:0 0 20px ${p.accent}30">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += tplCitation(slide.citation, p, 'center');
  h += '</div>';
  return h;
}

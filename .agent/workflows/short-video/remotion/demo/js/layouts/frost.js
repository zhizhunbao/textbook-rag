/* ═══════════════════════════════════════════════════════════════
 * frost.js — 霜冻玻璃布局 (毛玻璃卡片)
 * 依赖: render-utils.js
 * ═══════════════════════════════════════════════════════════════ */

function renderCover_frost(slide, p) {
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  h += `<div style="position:absolute;top:-80px;left:-100px;width:350px;height:350px;background:radial-gradient(circle,${p.accent}20,transparent 70%);border-radius:50%"></div>`;
  h += `<div style="position:absolute;bottom:-60px;right:-80px;width:280px;height:280px;background:radial-gradient(circle,${p.accentSecondary}18,transparent 70%);border-radius:50%"></div>`;
  h += `<div style="position:relative;z-index:2;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:24px;padding:60px 80px;max-width:1400px;width:80%">`;
  h += `<h1 style="font-size:70px;font-weight:700;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  if (slide.subtitle) h += `<p style="font-size:28px;color:${p.accentLight};margin-top:20px;font-weight:300;letter-spacing:1px;text-align:center">${slide.subtitle}</p>`;
  h += '</div></div>';
  return h;
}

function renderContent_frost(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  let h = '<div style="position:relative;width:100%;display:flex;flex-direction:column;align-items:center">';
  h += `<div style="position:absolute;top:-40px;right:-60px;width:200px;height:200px;background:radial-gradient(circle,${p.accent}15,transparent 70%);border-radius:50%"></div>`;
  h += `<h2 style="font-size:48px;font-weight:700;color:${p.textPrimary};margin:0 0 24px;text-align:center;position:relative;z-index:2">${slide.title}</h2>`;
  h += '<div style="position:relative;z-index:2;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:32px 40px;width:92%;display:flex;flex-direction:column;align-items:center">';
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += tplCitation(slide.citation, p, 'center') + '</div>';
  h += '</div>';
  return h;
}

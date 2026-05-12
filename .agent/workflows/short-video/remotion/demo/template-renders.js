/* ═══════════════════════════════════════════════════════════════
 * 模板渲染器 — 5 套独立布局 × 封面 + 内容页
 *
 * 布局差异:
 *   neon    — 居中堆叠 + 四角标记
 *   frost   — 毛玻璃卡片面板
 *   ember   — 左对齐社论风 (editorial)
 *   ocean   — 顶栏标题 + 下方内容分离
 *   minimal — 竖线分割 左对齐
 * ═══════════════════════════════════════════════════════════════ */

/* ── 通用工具 ── */
function tplBold(text, color) {
  return text.replace(
    /\*\*(.+?)\*\*/g,
    `<strong style="color:${color};font-weight:800">$1</strong>`
  );
}

function tplSource(src, p, align) {
  if (!src) return '';
  return `<div style="font-size:16px;color:${p.sourceText};margin-top:16px;text-align:${align || 'center'};word-break:break-all;max-width:90%;line-height:1.4;font-family:'Inter',monospace">${src}</div>`;
}

function tplCitation(cit, p, align) {
  if (!cit) return '';
  return `<div style="border-left:4px solid ${p.citationBorder};background:${p.citationBg};padding:12px 20px;border-radius:0 8px 8px 0;color:${p.citationText};font-size:22px;line-height:1.6;font-style:italic;margin-top:14px;text-align:${align || 'center'};max-width:95%">${cit}</div>`;
}

function tplTableHTML(table, p, dense) {
  const pad = dense ? '10px 16px' : '14px 24px';
  const thFs = dense ? 20 : 24;
  const tdFs = dense ? 24 : 28;
  let h = `<table style="width:100%;border-collapse:separate;border-spacing:0 5px;table-layout:fixed">`;
  h += '<thead><tr>';
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

function tplPoints(points, p, align, fs) {
  let h = `<ul style="font-size:${fs || 30}px;line-height:2;color:${p.textSecondary};margin:0;padding:0;list-style:none;text-align:${align || 'center'}">`;
  points.forEach(pt => { h += `<li>${tplBold(pt, p.accentLight)}</li>`; });
  h += '</ul>';
  return h;
}

function tplContent(slide, p, align, isCta) {
  if (!slide.content) return '';
  const fs = isCta ? 40 : 34;
  const clr = isCta ? p.accentLight : p.textSecondary;
  const fw = isCta ? 700 : 400;
  return `<p style="font-size:${fs}px;line-height:1.7;color:${clr};font-weight:${fw};margin:0;text-align:${align || 'center'}">${tplBold(slide.content, p.accentLight)}</p>`;
}

/* ═══════════════════════════════════════════════════════════════
 * 模板 1: NEON PULSE — 居中堆叠 + 四角标记
 * ═══════════════════════════════════════════════════════════════ */
function renderCover_neon(slide, p) {
  const glow = `0 0 40px ${p.accent}40, 0 0 80px ${p.accent}20`;
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  // 四角标
  h += `<div style="position:absolute;top:-20px;left:-40px;width:60px;height:60px;border-top:2px solid ${p.accent};border-left:2px solid ${p.accent}"></div>`;
  h += `<div style="position:absolute;top:-20px;right:-40px;width:60px;height:60px;border-top:2px solid ${p.accentSecondary};border-right:2px solid ${p.accentSecondary}"></div>`;
  h += `<div style="position:absolute;bottom:-20px;left:-40px;width:60px;height:60px;border-bottom:2px solid ${p.accentSecondary};border-left:2px solid ${p.accentSecondary}"></div>`;
  h += `<div style="position:absolute;bottom:-20px;right:-40px;width:60px;height:60px;border-bottom:2px solid ${p.accent};border-right:2px solid ${p.accent}"></div>`;
  h += `<h1 style="font-size:76px;font-weight:900;color:${p.textPrimary};text-shadow:${glow};letter-spacing:2px;line-height:1.15;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:400px;height:2px;margin:24px 0;background:linear-gradient(90deg,transparent,${p.accent},${p.accentSecondary},transparent)"></div>`;
  if (slide.subtitle) h += `<p style="font-size:26px;color:${p.accentLight};font-weight:400;letter-spacing:3px;text-transform:uppercase;margin:0">${slide.subtitle}</p>`;
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  return h;
}

function renderContent_neon(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  // 居中堆叠 + 细边框容器
  let h = `<div style="position:relative;border:1px solid ${p.accent}25;border-radius:4px;padding:12px;width:100%;display:flex;flex-direction:column;align-items:center">`;
  // 角标
  h += `<div style="position:absolute;top:-1px;left:-1px;width:20px;height:20px;border-top:2px solid ${p.accent};border-left:2px solid ${p.accent}"></div>`;
  h += `<div style="position:absolute;top:-1px;right:-1px;width:20px;height:20px;border-top:2px solid ${p.accent};border-right:2px solid ${p.accent}"></div>`;
  h += `<h2 style="font-size:48px;font-weight:900;color:${p.textPrimary};margin:0 0 24px;text-align:center;text-shadow:0 0 20px ${p.accent}30">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += tplCitation(slide.citation, p, 'center');
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
 * 模板 2: FROST GLASS — 毛玻璃卡片
 * ═══════════════════════════════════════════════════════════════ */
function renderCover_frost(slide, p) {
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  // 光球
  h += `<div style="position:absolute;top:-80px;left:-100px;width:350px;height:350px;background:radial-gradient(circle,${p.accent}20,transparent 70%);border-radius:50%"></div>`;
  h += `<div style="position:absolute;bottom:-60px;right:-80px;width:280px;height:280px;background:radial-gradient(circle,${p.accentSecondary}18,transparent 70%);border-radius:50%"></div>`;
  // 卡片
  h += `<div style="position:relative;z-index:2;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:24px;padding:60px 80px;max-width:1400px;width:80%">`;
  h += `<h1 style="font-size:70px;font-weight:700;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  if (slide.subtitle) h += `<p style="font-size:28px;color:${p.accentLight};margin-top:20px;font-weight:300;letter-spacing:1px;text-align:center">${slide.subtitle}</p>`;
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  h += '</div>';
  return h;
}

function renderContent_frost(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  // 毛玻璃卡片居中
  let h = '<div style="position:relative;width:100%;display:flex;flex-direction:column;align-items:center">';
  // 光球装饰
  h += `<div style="position:absolute;top:-40px;right:-60px;width:200px;height:200px;background:radial-gradient(circle,${p.accent}15,transparent 70%);border-radius:50%"></div>`;
  // 标题 (卡片外)
  h += `<h2 style="font-size:48px;font-weight:700;color:${p.textPrimary};margin:0 0 24px;text-align:center;position:relative;z-index:2">${slide.title}</h2>`;
  // 卡片内容
  h += `<div style="position:relative;z-index:2;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:20px;padding:32px 40px;width:92%;display:flex;flex-direction:column;align-items:center">`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += tplCitation(slide.citation, p, 'center');
  h += '</div>';
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
 * 模板 3: EMBER GLOW — 左对齐社论风
 * ═══════════════════════════════════════════════════════════════ */
function renderCover_ember(slide, p) {
  // 左对齐大标题
  let h = '<div style="display:flex;flex-direction:column;align-items:flex-start;justify-content:center;width:100%;padding-left:40px">';
  h += `<div style="width:120px;height:3px;background:linear-gradient(90deg,${p.accent},${p.accentSecondary});border-radius:2px;margin-bottom:36px"></div>`;
  h += `<h1 style="font-size:72px;font-weight:800;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:left;text-shadow:0 4px 30px ${p.accent}30">${slide.title}</h1>`;
  h += '<div style="display:flex;align-items:center;gap:16px;margin:28px 0">';
  h += `<div style="width:80px;height:1px;background:${p.accentSecondary}"></div>`;
  h += `<div style="width:10px;height:10px;background:${p.accent};transform:rotate(45deg)"></div>`;
  h += `<div style="width:80px;height:1px;background:${p.accentSecondary}"></div>`;
  h += '</div>';
  if (slide.subtitle) h += `<p style="font-size:28px;color:${p.accentSecondary};font-weight:400;letter-spacing:2px;margin:0;text-align:left">${slide.subtitle}</p>`;
  h += tplSource(slide.source, p, 'left');
  h += '</div>';
  return h;
}

function renderContent_ember(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  // 左对齐社论布局 — 标题左 + 渐变左边框
  let h = `<div style="width:100%;display:flex;flex-direction:column;align-items:flex-start;border-left:3px solid;border-image:linear-gradient(180deg,${p.accent},${p.accentSecondary}) 1;padding-left:36px">`;
  h += `<h2 style="font-size:48px;font-weight:800;color:${p.textPrimary};margin:0 0 24px;text-align:left">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'left', 28);
  if (slide.content) h += tplContent(slide, p, 'left', isCta);
  h += tplCitation(slide.citation, p, 'left');
  h += tplSource(slide.source, p, 'left');
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
 * 模板 4: OCEAN DEPTH — 顶栏标题 + 内容区分离
 * ═══════════════════════════════════════════════════════════════ */
function renderCover_ocean(slide, p) {
  let h = '<div style="position:relative;display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  // 水平波纹线
  h += `<div style="position:absolute;top:-30px;width:600px;height:3px;background:linear-gradient(90deg,transparent,${p.accent}60,transparent);border-radius:2px"></div>`;
  h += `<div style="position:absolute;top:-18px;width:400px;height:2px;background:linear-gradient(90deg,transparent,${p.accentSecondary}40,transparent);border-radius:2px"></div>`;
  h += `<h1 style="font-size:70px;font-weight:700;color:${p.textPrimary};letter-spacing:1px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:2px;height:40px;background:linear-gradient(180deg,${p.accent},transparent);margin:20px 0"></div>`;
  if (slide.subtitle) h += `<p style="font-size:30px;color:${p.accentLight};font-weight:400;letter-spacing:1px;margin:0;text-align:center">${slide.subtitle}</p>`;
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  return h;
}

function renderContent_ocean(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  // 顶栏标题条 + 内容区分离
  let h = '<div style="width:100%;display:flex;flex-direction:column;align-items:center">';
  // 标题栏 — 带底部渐变线
  h += `<div style="width:100%;padding-bottom:16px;margin-bottom:20px;border-bottom:2px solid;border-image:linear-gradient(90deg,transparent,${p.accent},transparent) 1;text-align:center">`;
  h += `<h2 style="font-size:48px;font-weight:700;color:${p.textPrimary};margin:0">${slide.title}</h2>`;
  h += '</div>';
  // 内容区
  h += '<div style="width:100%;display:flex;flex-direction:column;align-items:center">';
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'center');
  if (slide.content) h += tplContent(slide, p, 'center', isCta);
  h += '</div>';
  // 底部引用 + 来源
  h += `<div style="width:100%;margin-top:16px;padding-top:12px;border-top:1px solid ${p.accent}20;display:flex;flex-direction:column;align-items:center">`;
  h += tplCitation(slide.citation, p, 'center');
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
 * 模板 5: MINIMAL INK — 竖线分割 + 左对齐
 * ═══════════════════════════════════════════════════════════════ */
function renderCover_minimal(slide, p) {
  let h = '<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;width:100%">';
  h += `<div style="width:12px;height:12px;background:${p.accent};border-radius:50%;margin-bottom:40px"></div>`;
  h += `<h1 style="font-size:80px;font-weight:300;color:${p.textPrimary};letter-spacing:6px;line-height:1.2;margin:0;text-align:center">${slide.title}</h1>`;
  h += `<div style="width:60px;height:1px;background:${p.accentMuted};margin:32px 0"></div>`;
  if (slide.subtitle) h += `<p style="font-size:24px;color:${p.accentMuted};font-weight:300;letter-spacing:4px;margin:0;text-align:center">${slide.subtitle}</p>`;
  h += tplSource(slide.source, p, 'center');
  h += '</div>';
  return h;
}

function renderContent_minimal(slide, p) {
  const isCta = slide.type === 'cta' || slide.type === 'preview';
  const dense = slide.table && (slide.table.rows.length > 4 || slide.table.headers.length > 4);
  // 左竖线 + 大留白
  let h = '<div style="width:100%;display:flex;flex-direction:row;gap:40px">';
  // 左侧竖线 + 红点
  h += `<div style="display:flex;flex-direction:column;align-items:center;padding-top:8px">`;
  h += `<div style="width:8px;height:8px;background:${p.accent};border-radius:50%;flex-shrink:0"></div>`;
  h += `<div style="width:1px;flex:1;background:${p.accentMuted}40;margin-top:8px"></div>`;
  h += '</div>';
  // 右侧内容
  h += '<div style="flex:1;display:flex;flex-direction:column;align-items:flex-start">';
  h += `<h2 style="font-size:46px;font-weight:300;color:${p.textPrimary};margin:0 0 28px;text-align:left;letter-spacing:2px">${slide.title}</h2>`;
  if (slide.table) h += tplTableHTML(slide.table, p, dense);
  if (slide.points) h += tplPoints(slide.points, p, 'left', 28);
  if (slide.content) h += tplContent(slide, p, 'left', isCta);
  h += tplCitation(slide.citation, p, 'left');
  h += `<div style="margin-top:20px">${tplSource(slide.source, p, 'left')}</div>`;
  h += '</div>';
  h += '</div>';
  return h;
}

/* ═══ 分发器 ═══ */
function renderTemplateCover(slide, tpl) {
  const p = tpl.palette;
  switch (tpl.coverStyle) {
    case 'neon':    return renderCover_neon(slide, p);
    case 'frost':   return renderCover_frost(slide, p);
    case 'ember':   return renderCover_ember(slide, p);
    case 'ocean':   return renderCover_ocean(slide, p);
    case 'minimal': return renderCover_minimal(slide, p);
    default:        return renderCover_neon(slide, p);
  }
}

function renderTemplateContent(slide, tpl) {
  const p = tpl.palette;
  switch (tpl.contentStyle) {
    case 'neon':    return renderContent_neon(slide, p);
    case 'frost':   return renderContent_frost(slide, p);
    case 'ember':   return renderContent_ember(slide, p);
    case 'ocean':   return renderContent_ocean(slide, p);
    case 'minimal': return renderContent_minimal(slide, p);
    default:        return renderContent_neon(slide, p);
  }
}

/* ═══════════════════════════════════════════════════════════════
 * dispatcher.js — 布局分发器 (根据 tpl.coverStyle / tpl.contentStyle 选择渲染器)
 * 依赖: layouts/neon.js, frost.js, ember.js, ocean.js, minimal.js, competitor.js
 * ═══════════════════════════════════════════════════════════════ */

function renderTemplateCover(slide, tpl) {
  const p = tpl.palette;
  switch (tpl.coverStyle) {
    case 'neon':       return renderCover_neon(slide, p);
    case 'frost':      return renderCover_frost(slide, p);
    case 'ember':      return renderCover_ember(slide, p);
    case 'ocean':      return renderCover_ocean(slide, p);
    case 'minimal':    return renderCover_minimal(slide, p);
    case 'competitor': return renderCover_competitor(slide, p);
    default:           return renderCover_neon(slide, p);
  }
}

function renderTemplateContent(slide, tpl) {
  const p = tpl.palette;
  switch (tpl.contentStyle) {
    case 'neon':       return renderContent_neon(slide, p);
    case 'frost':      return renderContent_frost(slide, p);
    case 'ember':      return renderContent_ember(slide, p);
    case 'ocean':      return renderContent_ocean(slide, p);
    case 'minimal':    return renderContent_minimal(slide, p);
    case 'competitor': return renderContent_competitor(slide, p);
    default:           return renderContent_neon(slide, p);
  }
}

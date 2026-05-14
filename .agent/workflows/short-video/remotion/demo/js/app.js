/* ═══════════════════════════════════════════════════════════════
 * app.js — Layout Lab 主编排层
 * 职责: 加载 .md → 解析 → 渲染 → 控制面板绑定
 * 依赖: md-parser.js, palettes/*, render-utils.js, layouts/*
 * ═══════════════════════════════════════════════════════════════ */
(async function () {
  /* ── 预设数据集列表 ── */
  const PRESETS = [
    { id: 'generic',  label: '📊 通用示例',   file: 'slides/demo-generic.md' },
    { id: 'pnp',      label: '🍁 省提名PNP',  file: 'slides/demo-pnp.md' },
    { id: 'tech',     label: '💻 AI工具对比',  file: 'slides/demo-tech.md' },
    { id: 'minimal',  label: '🖤 极简生活',   file: 'slides/demo-minimal.md' },
  ];

  /* ── 状态 ── */
  let SLIDES = [];
  let currentSlide = 0;
  let currentPalette = 'competitor-gold';
  let currentLayout = 'competitor';
  let activePreset = '';

  const $ = (s) => document.querySelector(s);
  const slideArea = $('#slideArea');
  const subtitleText = $('#subtitleText');
  const slideSelect = $('#slideSelect');
  const specBox = $('#specBox');
  const canvas = $('#canvas');
  const tplDesc = $('#tplDesc');
  const paletteSelect = $('#paletteSelect');
  const layoutSelect = $('#layoutSelect');

  /* ── 渲染预设按钮 ── */
  function renderPresetButtons() {
    const box = $('#presetBtns');
    if (!box) return;
    box.innerHTML = '';
    PRESETS.forEach(p => {
      const btn = document.createElement('button');
      btn.textContent = p.label;
      btn.dataset.preset = p.id;
      btn.style.cssText = 'flex:1;min-width:100px;padding:6px 8px;font-size:12px;border-radius:6px;cursor:pointer;border:1px solid rgba(255,255,255,0.1);background:#1f2937;color:#e5e7eb;transition:all .15s';
      btn.addEventListener('click', () => switchPreset(p));
      box.appendChild(btn);
    });
  }

  function highlightPresetBtn(id) {
    const box = $('#presetBtns');
    if (!box) return;
    box.querySelectorAll('button').forEach(btn => {
      if (btn.dataset.preset === id) {
        btn.style.background = '#2563eb';
        btn.style.borderColor = '#3b82f6';
        btn.style.color = '#ffffff';
      } else {
        btn.style.background = '#1f2937';
        btn.style.borderColor = 'rgba(255,255,255,0.1)';
        btn.style.color = '#e5e7eb';
      }
    });
  }

  async function switchPreset(preset) {
    activePreset = preset.id;
    highlightPresetBtn(preset.id);
    await loadFromUrl(preset.file);
  }

  /* ── 加载 .md 并初始化 ── */
  async function loadFromUrl(url) {
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const text = await resp.text();
      loadMarkdown(text);
    } catch (e) {
      console.error('加载失败:', e);
      specBox.textContent = `❌ 加载失败: ${e.message}\n请检查文件是否存在`;
    }
  }

  function loadMarkdown(mdText) {
    const { meta, slides } = parseSlidesMarkdown(mdText);
    if (!slides || slides.length === 0) {
      specBox.textContent = '❌ 解析结果为空，请检查 .md 格式';
      return;
    }
    SLIDES = slides;

    /* 应用 frontmatter 默认值 */
    if (meta.template && PALETTES[meta.template]) {
      currentPalette = meta.template;
      paletteSelect.value = meta.template;
    }
    if (meta.layout) {
      currentLayout = meta.layout;
      layoutSelect.value = meta.layout;
    }

    /* 刷新 slide 下拉列表 */
    slideSelect.innerHTML = '';
    SLIDES.forEach((s, i) => {
      const opt = document.createElement('option');
      opt.value = i;
      opt.textContent = `[${i}] ${s.type}: ${(s.title || '').slice(0, 18)}`;
      slideSelect.appendChild(opt);
    });

    currentSlide = 0;
    renderSlide(0);
    $('#mdStatus').textContent = `✅ 已加载 ${SLIDES.length} 张幻灯片`;
  }

  /* ── 缩放画布适应窗口 ── */
  function fitCanvas() {
    const availW = window.innerWidth - 280 - 48;
    const availH = window.innerHeight - 48;
    const scale = Math.min(availW / 1920, availH / 1080, 1);
    canvas.style.transform = `scale(${scale})`;
  }
  window.addEventListener('resize', fitCanvas);

  /* ── 构造虚拟模板对象 (配色 + 布局 混搭) ── */
  function buildTpl() {
    const base = PALETTES[currentPalette];
    return { ...base, coverStyle: currentLayout, contentStyle: currentLayout };
  }

  /* ── 渲染幻灯片 ── */
  function renderSlide(idx) {
    if (!SLIDES[idx]) return;
    const slide = SLIDES[idx];
    const tpl = buildTpl();
    const p = tpl.palette;
    let html = '';

    if (slide.type === 'cover') {
      slideArea.style.background = p.bgCover;
      html = renderTemplateCover(slide, tpl);
    } else {
      slideArea.style.background = p.bgGradient;
      html = renderTemplateContent(slide, tpl);
    }

    slideArea.innerHTML = html;

    /* URL 右上角水印 (所有布局) */
    if (slide.source) {
      const wm = document.createElement('div');
      wm.style.cssText = `position:absolute;top:16px;right:80px;font-size:18px;color:${p.sourceText || 'rgba(255,255,255,0.3)'};font-family:'Inter',monospace;line-height:1;text-align:right;white-space:nowrap;z-index:10`;
      wm.textContent = slide.source;
      slideArea.appendChild(wm);
    }

    subtitleText.textContent = slide._subtitle_text || '';
    subtitleText.style.color = p.subtitleText;
    $('#subtitleArea').style.background = p.subtitleBg;
    slideSelect.value = idx;
    updateSpec(slide, tpl, p);
    updateDesc(tpl);
  }

  /* ── 规格标注 ── */
  function updateSpec(slide, tpl, p) {
    const layoutNames = {
      neon: '居中堆叠+角标', frost: '毛玻璃卡片', ember: '左对齐社论风',
      ocean: '顶栏分离式', minimal: '竖线左排版', competitor: '数据优先+金线',
    };
    const lines = [
      `配色: ${tpl.palette.name}`, `布局: ${layoutNames[currentLayout] || currentLayout}`,
      `类型: ${slide.type}`, `─────────────────`,
      `画布: 1920×1080`, `幻灯片区: 1920×880`, `字幕区: 1920×200`,
      `─────────────────`, `主色: ${p.accent}`, `亮色: ${p.accentLight}`,
      `辅色: ${p.accentSecondary || 'N/A'}`,
    ];
    specBox.textContent = lines.join('\n');
  }

  function updateDesc(tpl) {
    const layoutDesc = {
      neon: '居中堆叠布局 · 四角霓虹边框装饰', frost: '毛玻璃卡片布局 · 模糊光球装饰',
      ember: '左对齐社论布局 · 渐变左边框', ocean: '顶栏标题 + 底部引用分离布局',
      minimal: '竖线 + 红点 · 左对齐大留白', competitor: '数据优先布局 · 金色装饰线 · URL右上角水印',
    };
    tplDesc.innerHTML = `<strong>${tpl.palette.name}</strong> × ${layoutDesc[currentLayout] || currentLayout}`;
  }

  /* ── 尺寸标注 ── */
  function renderSizeAnnotations() {
    const box = $('#sizeAnnotations');
    box.innerHTML = '';
    [
      { x: 960, y: 10, text: '1920px 宽' }, { x: 1930, y: 440, text: '880px 幻灯片区' },
      { x: 1930, y: 980, text: '200px 字幕区' }, { x: 10, y: 50, text: '60px top-pad' },
      { x: 10, y: 860, text: '24px bot-pad' }, { x: 82, y: 30, text: '80px left-pad' },
    ].forEach(t => {
      const el = document.createElement('div');
      el.className = 'size-tag';
      el.textContent = t.text;
      el.style.left = t.x + 'px';
      el.style.top = t.y + 'px';
      box.appendChild(el);
    });
  }

  /* ── 事件绑定 ── */
  slideSelect.addEventListener('change', () => { currentSlide = +slideSelect.value; renderSlide(currentSlide); });
  paletteSelect.addEventListener('change', () => { currentPalette = paletteSelect.value; renderSlide(currentSlide); });
  layoutSelect.addEventListener('change', () => { currentLayout = layoutSelect.value; renderSlide(currentSlide); });
  $('#prevBtn').addEventListener('click', () => { currentSlide = (currentSlide - 1 + SLIDES.length) % SLIDES.length; renderSlide(currentSlide); });
  $('#nextBtn').addEventListener('click', () => { currentSlide = (currentSlide + 1) % SLIDES.length; renderSlide(currentSlide); });
  $('#showGuides').addEventListener('change', (e) => { $('#guides').classList.toggle('hidden', !e.target.checked); });
  $('#showSizes').addEventListener('change', (e) => { $('#sizeAnnotations').classList.toggle('hidden', !e.target.checked); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') $('#prevBtn').click();
    if (e.key === 'ArrowRight') $('#nextBtn').click();
  });

  /* ── 文件加载器 ── */
  const fileInput = $('#mdFileInput');
  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      activePreset = '';
      highlightPresetBtn('');
      const text = await file.text();
      loadMarkdown(text);
    });
  }

  const pasteBtn = $('#mdPasteBtn');
  const pasteArea = $('#mdPasteArea');
  if (pasteBtn && pasteArea) {
    pasteBtn.addEventListener('click', () => {
      const text = pasteArea.value.trim();
      if (text) {
        activePreset = '';
        highlightPresetBtn('');
        loadMarkdown(text);
      }
    });
  }

  /* ── 启动 ── */
  renderPresetButtons();
  renderSizeAnnotations();
  fitCanvas();
  /* 默认加载第一个预设 */
  await switchPreset(PRESETS[0]);
})();

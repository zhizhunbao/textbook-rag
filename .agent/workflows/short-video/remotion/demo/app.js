/* ── 主逻辑 (配色 × 布局 自由组合) ── */
(function () {
  let currentSlide = 0;
  let currentPalette = 'neon-pulse';   // 配色方案 key
  let currentLayout = 'neon';          // 布局风格 key

  const $ = (s) => document.querySelector(s);
  const slideArea = $('#slideArea');
  const subtitleText = $('#subtitleText');
  const slideSelect = $('#slideSelect');
  const specBox = $('#specBox');
  const canvas = $('#canvas');
  const tplDesc = $('#tplDesc');

  // ── 初始化页面下拉 ──
  DEMO_SLIDES.forEach((s, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = `[${i}] ${s.type}: ${s.title.slice(0, 18)}`;
    slideSelect.appendChild(opt);
  });

  // ── 缩放画布适应窗口 ──
  function fitCanvas() {
    const availW = window.innerWidth - 280 - 48;
    const availH = window.innerHeight - 48;
    const scale = Math.min(availW / 1920, availH / 1080, 1);
    canvas.style.transform = `scale(${scale})`;
  }
  window.addEventListener('resize', fitCanvas);

  // ── 构造虚拟模板对象 (配色 + 布局 混搭) ──
  function buildTpl() {
    const base = TEMPLATES[currentPalette];
    return {
      ...base,
      coverStyle: currentLayout,
      contentStyle: currentLayout,
    };
  }

  // ── 渲染幻灯片 ──
  function renderSlide(idx) {
    const slide = DEMO_SLIDES[idx];
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
    subtitleText.textContent = slide._subtitle_text || '';
    subtitleText.style.color = p.subtitleText;
    $('#subtitleArea').style.background = p.subtitleBg;
    slideSelect.value = idx;
    updateSpec(slide, tpl, p);
    updateDesc(tpl);
  }

  // ── 规格标注 ──
  function updateSpec(slide, tpl, p) {
    const layoutNames = {
      neon: '居中堆叠+角标', frost: '毛玻璃卡片',
      ember: '左对齐社论风', ocean: '顶栏分离式', minimal: '竖线左排版',
    };
    const lines = [
      `配色: ${tpl.palette.name}`,
      `布局: ${layoutNames[currentLayout] || currentLayout}`,
      `类型: ${slide.type}`,
      `─────────────────`,
      `画布: 1920×1080`,
      `幻灯片区: 1920×880`,
      `字幕区: 1920×200`,
      `─────────────────`,
      `主色: ${p.accent}`,
      `亮色: ${p.accentLight}`,
      `辅色: ${p.accentSecondary || 'N/A'}`,
    ];
    specBox.textContent = lines.join('\n');
  }

  // ── 模板描述 ──
  function updateDesc(tpl) {
    const layoutDesc = {
      neon: '居中堆叠布局 · 四角霓虹边框装饰',
      frost: '毛玻璃卡片布局 · 模糊光球装饰',
      ember: '左对齐社论布局 · 渐变左边框',
      ocean: '顶栏标题 + 底部引用分离布局',
      minimal: '竖线 + 红点 · 左对齐大留白',
    };
    tplDesc.innerHTML = `<strong>${tpl.palette.name}</strong> × ${layoutDesc[currentLayout] || currentLayout}`;
  }

  // ── 尺寸标注 ──
  function renderSizeAnnotations() {
    const box = $('#sizeAnnotations');
    box.innerHTML = '';
    [
      { x: 960, y: 10, text: '1920px 宽' },
      { x: 1930, y: 440, text: '880px 幻灯片区' },
      { x: 1930, y: 980, text: '200px 字幕区' },
      { x: 10, y: 50, text: '60px top-pad' },
      { x: 10, y: 860, text: '24px bot-pad' },
      { x: 82, y: 30, text: '80px left-pad' },
    ].forEach(t => {
      const el = document.createElement('div');
      el.className = 'size-tag';
      el.textContent = t.text;
      el.style.left = t.x + 'px';
      el.style.top = t.y + 'px';
      box.appendChild(el);
    });
  }

  // ── 事件绑定 ──
  slideSelect.addEventListener('change', () => {
    currentSlide = +slideSelect.value;
    renderSlide(currentSlide);
  });
  $('#paletteSelect').addEventListener('change', () => {
    currentPalette = $('#paletteSelect').value;
    renderSlide(currentSlide);
  });
  $('#layoutSelect').addEventListener('change', () => {
    currentLayout = $('#layoutSelect').value;
    renderSlide(currentSlide);
  });
  $('#prevBtn').addEventListener('click', () => {
    currentSlide = (currentSlide - 1 + DEMO_SLIDES.length) % DEMO_SLIDES.length;
    renderSlide(currentSlide);
  });
  $('#nextBtn').addEventListener('click', () => {
    currentSlide = (currentSlide + 1) % DEMO_SLIDES.length;
    renderSlide(currentSlide);
  });
  $('#showGuides').addEventListener('change', (e) => {
    $('#guides').classList.toggle('hidden', !e.target.checked);
  });
  $('#showSizes').addEventListener('change', (e) => {
    $('#sizeAnnotations').classList.toggle('hidden', !e.target.checked);
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') $('#prevBtn').click();
    if (e.key === 'ArrowRight') $('#nextBtn').click();
  });

  // ── 启动 ──
  renderSizeAnnotations();
  renderSlide(0);
  fitCanvas();
})();

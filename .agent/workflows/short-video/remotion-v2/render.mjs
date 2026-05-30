/**
 * render.mjs — 短视频渲染入口 (v2 — storyline.md 唯一数据源)
 *
 * 用法:
 *   node render.mjs --data ../../../../data/short-videos/{slug}
 *
 * 功能:
 *   1. 从 storyline.md 自动解析 slides + narration 台词
 *   2. 匹配 timestamps.json 的 slide_index
 *   3. 复制 narration.wav 到 public/audio.wav
 *   4. 调用 npx remotion render 输出 final.mp4
 *
 * 兼容: 如无 storyline.md 则回退到 slides.json + script.txt (旧流程)
 */

import { readFileSync, copyFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { resolve, join } from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));

// ── 解析参数 ──
const args = process.argv.slice(2);
const dataIdx = args.indexOf('--data');
if (dataIdx === -1 || !args[dataIdx + 1]) {
  console.error('用法: node render.mjs --data <data-dir>');
  console.error('示例: node render.mjs --data ../../../../data/short-videos/sp-cost-quick');
  process.exit(1);
}

const dataDir = resolve(process.cwd(), args[dataIdx + 1]);
const publicDir = resolve(__dirname, 'public');
const outputDir = resolve(dataDir, 'output');

console.log(`📂 数据目录: ${dataDir}`);

// ── 解析 storyline.md ──────────────────────────────────────

function parseStoryline(mdText) {
  const slides = [];
  const narrationLines = [];  // 每行台词 + slide_index
  let text = mdText.replace(/\r\n/g, '\n').trim();

  // 解析作者水印
  const authorMatch = text.match(/\*\*(?:作者|Author)\*\*:\s*(.+)/m);
  const watermark = authorMatch ? authorMatch[1].trim() : '';

  // 解析主题色 (可选字段: **主题色**: ocean)
  const themeMatch = text.match(/\*\*(?:主题色|Theme)\*\*:\s*(\w+)/m);
  const themeName = themeMatch ? themeMatch[1].trim().toLowerCase() : 'gold';

  // 截断引用汇总
  const summaryIdx = text.search(/^## 📋/m);
  if (summaryIdx > -1) text = text.slice(0, summaryIdx);

  // 按 --- 分页
  const pages = text.split(/^---$/m).map(p => p.trim()).filter(Boolean);

  let slideIndex = -1;  // 第一页会变成 0

  for (const page of pages) {
    // 检测 ## [type] 标题
    const typeMatch = page.match(/^## \[(\w+)\]\s*(.*)/m);
    if (!typeMatch) {
      // 可能是元数据区 (# H1 + > metadata)，跳过
      continue;
    }

    slideIndex++;
    const type = typeMatch[1];    // cover, argument, evidence, cta, preview
    const title = typeMatch[2].trim();

    const slide = { type, title, source: '', chapter: undefined };

    // 提取 **副标题**
    const subMatch = page.match(/\*\*(?:副标题|Subtitle)\*\*:\s*(.+)/);
    if (subMatch) slide.subtitle = subMatch[1].trim();

    // 提取 **钩子数字** / **钩子单位**
    const hookNumMatch = page.match(/\*\*(?:钩子数字|Hook Number)\*\*:\s*(.+)/);
    if (hookNumMatch) slide.hookNumber = hookNumMatch[1].trim();
    const hookUnitMatch = page.match(/\*\*(?:钩子单位|Hook Unit)\*\*:\s*(.+)/);
    if (hookUnitMatch) slide.hookUnit = hookUnitMatch[1].trim();

    // 提取 **内容**
    const contentMatch = page.match(/\*\*(?:内容|Content)\*\*:\s*(.+)/);
    if (contentMatch) slide.content = contentMatch[1].trim();

    // 提取 **章节** (用于章节时间轴的短标签)
    const chapterMatch = page.match(/\*\*(?:章节|Chapter)\*\*:\s*(.+)/);
    if (chapterMatch) slide.chapter = chapterMatch[1].trim();

    // ── 提取所有 **台词**: 块的行数，用于计算 cropImages triggerLine ──
    // 每个引用块的 triggerLine = 该引用块对应的台词在 slide 内的起始行号
    // 需要按出现顺序收集 (引用N + 台词) 对
    const citationBlocks = [];
    const citBlockPattern = /\*\*引用\s*(\d+)\*\*:\s*"[^"]+"\s*\n\*\*来源\*\*:\s*(https?\S+)(?:\s*\n\*\*本地\*\*:\s*\S+)?\s*\n!\[截图\]\(([^)]+)\)(?:\s*\n\*\*bbox\*\*:\s*\[([^\]]+)\])?(?:\s*\n\*\*pageSize\*\*:\s*\[([^\]]+)\])?/g;
    let citBlockMatch;
    while ((citBlockMatch = citBlockPattern.exec(page)) !== null) {
      const entry = {
        citIndex: parseInt(citBlockMatch[1]),
        sourceUrl: citBlockMatch[2].trim(),
        imgPath: citBlockMatch[3].trim(),
        matchEnd: citBlockMatch.index + citBlockMatch[0].length,
      };
      // Parse bbox and pageSize if present (written by extract_screenshots.py)
      if (citBlockMatch[4]) {
        entry.bbox = citBlockMatch[4].split(',').map(s => parseFloat(s.trim()));
      }
      if (citBlockMatch[5]) {
        entry.pageSize = citBlockMatch[5].split(',').map(s => parseFloat(s.trim()));
      }
      citationBlocks.push(entry);
    }

    // 提取所有 **台词**: 块及其在 page 中的位置
    const narrationBlocks = [];
    const narrationPattern = /\*\*(?:台词|Narration)\*\*:\s*\n([\s\S]*?)(?=\n\*\*|$)/g;
    let narMatch;
    while ((narMatch = narrationPattern.exec(page)) !== null) {
      const lines = narMatch[1].split('\n').map(l => l.trim()).filter(Boolean);
      narrationBlocks.push({
        startPos: narMatch.index,
        lines,
      });
    }

    // 为每个引用块找到紧跟其后的台词块，计算 triggerLine
    const cropImages = [];
    let cumulativeLineCount = 0;
    let lastNarBlockIdx = -1;

    for (const citBlock of citationBlocks) {
      // 找到紧跟在此引用后面的台词块
      let narBlock = null;
      for (let ni = 0; ni < narrationBlocks.length; ni++) {
        if (narrationBlocks[ni].startPos > citBlock.matchEnd && ni > lastNarBlockIdx) {
          narBlock = narrationBlocks[ni];
          lastNarBlockIdx = ni;
          break;
        }
      }

      // triggerLine = 截图应在 slide 内第几句台词时出现
      // 第一个引用的截图在第 1 句台词时出现
      const triggerLine = cumulativeLineCount + 1;

      let sourceLabel = '官方网站';
      if (citBlock.sourceUrl.includes('canada.ca')) {
        if (citBlock.sourceUrl.includes('immigration-refugees-citizenship')) sourceLabel = 'IRCC';
        else sourceLabel = 'Government of Canada';
      }
      const cropEntry = {
        src: citBlock.imgPath,
        triggerLine,
        sourceLabel,
      };
      // Inject bbox/pageSize from storyline metadata (written by extract_screenshots.py)
      if (citBlock.bbox) cropEntry.bbox = citBlock.bbox;
      if (citBlock.pageSize) cropEntry.pageSize = citBlock.pageSize;
      cropImages.push(cropEntry);

      // 累加这个台词块的行数
      if (narBlock) {
        cumulativeLineCount += narBlock.lines.length;
      }
    }

    if (cropImages.length > 0) {
      slide.cropImages = cropImages;
    }

    // 右上角水印: 固定显示作者频道名
    slide.source = watermark;

    // 提取表格
    const tableLines = page.split('\n').filter(l => l.trim().startsWith('|'));
    if (tableLines.length >= 3) {
      const parseRow = (line) => {
        const parts = line.split('|').map(s => s.trim().replace(/\\(.)/g, '$1'));
        // strip leading/trailing empty strings from | ... | syntax, but keep interior empties
        if (parts.length > 0 && parts[0] === '') parts.shift();
        if (parts.length > 0 && parts[parts.length - 1] === '') parts.pop();
        return parts;
      };
      const headers = parseRow(tableLines[0]);
      const rows = tableLines.slice(2).map(parseRow).filter(r => r.length > 0); // skip separator
      if (rows.length > 0) slide.table = { headers, rows };
    }
    // 提取所有台词行 (合并所有 **台词** 块)
    for (const nb of narrationBlocks) {
      let isFirst = (narrationLines.filter(nl => nl.slide_index === slideIndex).length === 0);
      for (const line of nb.lines) {
        narrationLines.push({ text: line, slide_index: slideIndex, is_first: isFirst });
        isFirst = false;
      }
    }

    slides.push(slide);
  }

  return { slides, narrationLines, themeName };
}

// ── 主流程 ──────────────────────────────────────────────────

const storylinePath = join(dataDir, 'storyline.md');
const slidesJsonPath = join(dataDir, 'slides.json');
const tsPath = join(dataDir, 'narration', 'timestamps.json');
const audioPath = join(dataDir, 'narration', 'narration.wav');

// 验证音频和时间戳
for (const [name, path] of [['timestamps.json', tsPath], ['narration.wav', audioPath]]) {
  if (!existsSync(path)) {
    console.error(`❌ 缺少文件: ${name} (${path})`);
    process.exit(1);
  }
}

let slides;
let narrationLines = null;

if (existsSync(storylinePath)) {
  // ── v2: 从 storyline.md 解析 ──
  console.log('📖 使用 storyline.md (v2 模式)');
  const md = readFileSync(storylinePath, 'utf-8');
  const parsed = parseStoryline(md);
  slides = parsed.slides;
  narrationLines = parsed.narrationLines;
  console.log(`   ${slides.length} slides, ${narrationLines.length} narration lines`);
} else if (existsSync(slidesJsonPath)) {
  // ── v1: 从 slides.json 解析 (回退) ──
  console.log('⚠️  storyline.md 不存在，回退到 slides.json (v1 模式)');
  const raw = JSON.parse(readFileSync(slidesJsonPath, 'utf-8'));
  slides = raw.slides || raw;
} else {
  console.error('❌ 缺少 storyline.md 或 slides.json');
  process.exit(1);
}

// ── 读取 timestamps 并匹配 slide_index ──
const timestamps = JSON.parse(readFileSync(tsPath, 'utf-8'));

if (narrationLines) {
  // storyline 模式: 台词行与 timestamps 1:1 顺序对应，直接按索引映射
  if (timestamps.length === narrationLines.length) {
    // 完全对齐 — 直接赋值
    for (let i = 0; i < timestamps.length; i++) {
      timestamps[i].slide_index = narrationLines[i].slide_index;
    }
  } else {
    // 长度不一致 — 按顺序贪心匹配，保证 slide_index 单调不减
    const cleanForMatch = (s) => s.replace(/[，。！？、；：""''（）《》【】…—·\u3000\s]/g, '');
    let nlIdx = 0;
    for (const ts of timestamps) {
      const cleanTs = cleanForMatch(ts.text);
      let matched = false;

      // 从当前位置向前搜索（不回头）
      for (let j = nlIdx; j < narrationLines.length; j++) {
        const cleanNl = cleanForMatch(narrationLines[j].text);
        if (cleanNl === cleanTs || cleanNl.includes(cleanTs) || cleanTs.includes(cleanNl)) {
          ts.slide_index = narrationLines[j].slide_index;
          nlIdx = j;  // 下次从这里继续，不会回头
          matched = true;
          break;
        }
      }

      if (!matched) {
        // 回退: 使用上一个 timestamp 的 slide_index（单调不减）
        const idx = timestamps.indexOf(ts);
        ts.slide_index = idx > 0 ? timestamps[idx - 1].slide_index : 0;
      }
    }
  }
} else {
  // v1 回退: 从 script.txt 匹配 (旧逻辑)
  const scriptPath = join(dataDir, 'script.txt');
  if (existsSync(scriptPath)) {
    const scriptLines = readFileSync(scriptPath, 'utf-8')
      .split(/\r?\n/)
      .filter(l => l.trim() && !l.startsWith('#'));
    let slideIdx = 0;
    const lineSlideMap = [];
    for (const line of scriptLines) {
      if (line.includes('|')) slideIdx = lineSlideMap.length === 0 ? 0 : slideIdx + 1;
      lineSlideMap.push(slideIdx);
    }
    const lineTexts = scriptLines.map(l => l.split('|')[0].trim().replace(/[，。！？、；：""''（）《》【】…—·\u3000]/g, ''));
    for (const ts of timestamps) {
      const cleanTs = ts.text.replace(/[，。！？、；：""''（）《》【】…—·\u3000\s]/g, '');
      for (let i = 0; i < lineTexts.length; i++) {
        if (lineTexts[i].replace(/\s/g, '') === cleanTs) {
          ts.slide_index = lineSlideMap[i];
          break;
        }
      }
    }
  }
}

// 日志: slide_index 映射
console.log('🗂️  slide_index 映射:');
const slideMap = {};
for (const ts of timestamps) {
  const si = ts.slide_index ?? 0;
  if (!slideMap[si]) slideMap[si] = [];
  slideMap[si].push(ts.text.substring(0, 15) + '...');
}
for (const [idx, texts] of Object.entries(slideMap)) {
  const slideTitle = slides[idx]?.title || '???';
  console.log(`   Slide ${idx} [${slideTitle.substring(0, 12)}]: ${texts.length} lines`);
}

// ── 准备 public/ ──
mkdirSync(publicDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

copyFileSync(audioPath, join(publicDir, 'audio.wav'));
console.log('🔊 音频已复制到 public/audio.wav');

// ── 计算章节时间轴数据 ──
// 优先读取 storyline 中 **章节**: 字段 (作者手动定义)
// 如果没有任何 **章节** 字段，则自动计算 (跳过引用/预告, 合并同前缀)

const hasExplicitChapters = slides.some(s => s.chapter);
let chapters = [];

if (hasExplicitChapters) {
  // ── 模式A: 作者在 storyline 中用 **章节**: 标签 手动定义 ──
  console.log('📖 使用 storyline 中的 **章节** 字段');
  for (let si = 0; si < slides.length; si++) {
    if (!slides[si].chapter) continue;
    const firstTs = timestamps.find(ts => ts.slide_index === si);
    if (!firstTs) continue;
    chapters.push({
      title: slides[si].chapter,
      startSec: firstTs.start,
      slideIndex: si,
    });
  }
} else {
  // ── 模式B: 自动计算 (通用回退) ──
  console.log('🤖 自动计算章节 (无 **章节** 字段)');
  const rawChapters = [];
  for (let si = 0; si < slides.length; si++) {
    const slide = slides[si];
    const title = slide.title || '';

    // 跳过引用来源页
    if (/引用来源|引用|参考|Sources|References|Citations/.test(title)) continue;
    // 跳过 disclaimer / preview / citation 页
    if (['preview', 'disclaimer', 'citation'].includes(slide.type)) continue;

    const firstTs = timestamps.find(ts => ts.slide_index === si);
    if (!firstTs) continue;

    // 提取合并用的前缀 (去掉序号后缀)
    const prefix = title
      .replace(/[（(][一二三四五六七八九十\d]+[）)]/g, '')
      .split(/[：:]/)[0]
      .trim();

    rawChapters.push({
      title: slide.type === 'cover' ? '开场' : title,
      prefix: slide.type === 'cover' ? '__cover__' : prefix,
      startSec: firstTs.start,
      slideIndex: si,
    });
  }

  // 合并同前缀的连续章节
  for (const ch of rawChapters) {
    const prev = chapters[chapters.length - 1];
    if (prev && prev.prefix === ch.prefix) continue;
    chapters.push({ ...ch });
  }
}

console.log(`📊 章节时间轴: ${chapters.length} 个章节`);
for (const ch of chapters) {
  console.log(`   ${ch.startSec.toFixed(1)}s → ${ch.title}`);
}

// ── 复制 storyline 中引用的截图到 public/ ──────────────────────
// parseStoryline() 已从 ![截图] 提取 cropImages，这里只需复制 PNG 文件
const publicPagesDir = join(publicDir, 'pages');
mkdirSync(publicPagesDir, { recursive: true });

let copiedCount = 0;
const copiedPaths = new Set();
for (const slide of slides) {
  if (!slide.cropImages) continue;
  for (const crop of slide.cropImages) {
    if (copiedPaths.has(crop.src)) continue;
    const srcPng = join(dataDir, crop.src);
    const dstPng = join(publicDir, crop.src);
    if (existsSync(srcPng)) {
      copyFileSync(srcPng, dstPng);
      copiedCount++;
      copiedPaths.add(crop.src);
    } else {
      console.warn(`   ⚠️ 截图不存在: ${srcPng}`);
    }
  }
}

const slidesWithCrops = slides.filter(s => s.cropImages && s.cropImages.length > 0);
if (slidesWithCrops.length > 0) {
  console.log(`\n📸 证据截图模式: ${slidesWithCrops.length} 个 slide 有截图, 共复制 ${copiedCount} 张 PNG`);
  for (const s of slidesWithCrops) {
    const idx = slides.indexOf(s);
    console.log(`   Slide ${idx} [${s.title.substring(0, 15)}]: ${s.cropImages.length} 张截图`);
  }
} else {
  console.log('\n📝 无截图引用，使用纯文本模式');
}

console.log('\n✅ bbox/pageSize 数据已从 storyline.md 直接解析');

// ── 构建 props ──
// 主题色: 从 storyline 元数据解析，默认 gold
const themeName = (existsSync(storylinePath) && narrationLines)
  ? parseStoryline(readFileSync(storylinePath, 'utf-8')).themeName
  : 'gold';
console.log(`🎨 主题色: ${themeName}`);

const props = {
  slides,
  timestamps,
  audioUrl: '/public/audio.wav',
  chapters,
  themeName,
};

const propsPath = join(__dirname, 'input-props.json');
writeFileSync(propsPath, JSON.stringify(props, null, 2));
console.log(`📝 Props 已写入: ${propsPath}`);

// ── 渲染 ──
const outputPath = join(outputDir, 'final.mp4');
const cmd = [
  'npx', 'remotion', 'render',
  'src/index.ts',
  'ShortVideo',
  `--props=${propsPath}`,
  `--output=${outputPath}`,
  '--codec=h264',
  '--image-format=jpeg',
  '--jpeg-quality=90',
].join(' ');

console.log(`🎬 开始渲染...`);
console.log(`   ${cmd}\n`);

try {
  execSync(cmd, { cwd: __dirname, stdio: 'inherit' });
  console.log(`\n✅ 渲染完成: ${outputPath}`);
} catch (e) {
  console.error('\n❌ 渲染失败');
  process.exit(1);
}

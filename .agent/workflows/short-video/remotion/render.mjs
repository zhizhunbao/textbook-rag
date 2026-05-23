#!/usr/bin/env node
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

    // **引用** 是作者参考文本，不显示在视频中，跳过

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

    // 提取 **台词**: 块
    const narrationMatch = page.match(/\*\*(?:台词|Narration)\*\*:\s*\n([\s\S]*?)(?=\n\*\*|\n---|\n##|$)/);
    if (narrationMatch) {
      const lines = narrationMatch[1].split('\n').map(l => l.trim()).filter(Boolean);
      let isFirst = true;
      for (const line of lines) {
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

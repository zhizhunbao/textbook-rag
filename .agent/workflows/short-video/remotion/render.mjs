#!/usr/bin/env node
/**
 * render.mjs — 短视频渲染入口
 *
 * 用法:
 *   node render.mjs --data ../../../../data/short-videos/{slug}
 *
 * 功能:
 *   1. 从 data 目录读取 slides.json / timestamps.json / script.txt
 *   2. 复制 narration.wav 到 public/audio.wav
 *   3. 构建 props 并写入临时文件
 *   4. 调用 npx remotion render 输出 final.mp4
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
  console.error('示例: node render.mjs --data ../../../../data/short-videos/pnp');
  process.exit(1);
}

const dataDir = resolve(__dirname, args[dataIdx + 1]);
const publicDir = resolve(__dirname, 'public');
const outputDir = resolve(dataDir, 'output');

console.log(`📂 数据目录: ${dataDir}`);

// ── 验证必要文件 ──
const slidesPath = join(dataDir, 'slides.json');
const tsPath = join(dataDir, 'narration', 'timestamps.json');
const audioPath = join(dataDir, 'narration', 'narration.wav');

for (const [name, path] of [['slides.json', slidesPath], ['timestamps.json', tsPath], ['narration.wav', audioPath]]) {
  if (!existsSync(path)) {
    console.error(`❌ 缺少文件: ${name} (${path})`);
    process.exit(1);
  }
}

// ── 读取数据 ──
const slides = JSON.parse(readFileSync(slidesPath, 'utf-8'));
const timestamps = JSON.parse(readFileSync(tsPath, 'utf-8'));

// ── 读取 script.txt 并计算 slide_index 映射 ──
const scriptPath = join(dataDir, 'script.txt');
if (existsSync(scriptPath)) {
  const scriptLines = readFileSync(scriptPath, 'utf-8')
    .split(/\r?\n/)
    .filter(l => l.trim() && !l.startsWith('#'));  // 忽略空行和标题

  // 解析 script.txt: 带 | 的行标记新幻灯片开始
  // 构建 lineIndex → slideIndex 映射
  let slideIdx = 0;
  const lineSlideMap = []; // lineSlideMap[i] = 该行对应的 slide index
  for (const line of scriptLines) {
    if (line.includes('|')) {
      slideIdx = lineSlideMap.length === 0 ? 0 : slideIdx + 1;
    }
    lineSlideMap.push(slideIdx);
  }

  // 提取每行的纯文本 (去除 | 后面的标记)
  const lineTexts = scriptLines.map(l => {
    let text = l.split('|')[0].trim();
    // 去掉标点以便模糊匹配
    return text.replace(/[，。！？、；：""''（）《》【】…—·\u3000]/g, '');
  });

  // 无空格版本用于更可靠的匹配 (TTS 会把标点变成空格)
  const lineTextsNoSpace = lineTexts.map(t => t.replace(/\s+/g, ''));

  // 给每个 timestamp 匹配 slide_index
  for (const ts of timestamps) {
    if (ts.slide_index !== undefined) continue; // 已有则跳过
    const cleanTs = ts.text.replace(/[，。！？、；：""''（）《》【】…—·\u3000]/g, '');
    const cleanTsNoSpace = cleanTs.replace(/\s+/g, '');
    // 尝试精确匹配 (含空格)
    let matched = false;
    for (let i = 0; i < lineTexts.length; i++) {
      if (lineTexts[i] === cleanTs) {
        ts.slide_index = lineSlideMap[i];
        matched = true;
        break;
      }
    }
    // 无空格精确匹配
    if (!matched) {
      for (let i = 0; i < lineTextsNoSpace.length; i++) {
        if (lineTextsNoSpace[i] === cleanTsNoSpace) {
          ts.slide_index = lineSlideMap[i];
          matched = true;
          break;
        }
      }
    }
    // 模糊匹配: 无空格 includes
    if (!matched) {
      for (let i = 0; i < lineTextsNoSpace.length; i++) {
        if (lineTextsNoSpace[i].includes(cleanTsNoSpace) || cleanTsNoSpace.includes(lineTextsNoSpace[i])) {
          ts.slide_index = lineSlideMap[i];
          matched = true;
          break;
        }
      }
    }
    if (!matched) {
      // 回退: 使用上一个 timestamp 的 slide_index
      const prevTs = timestamps[timestamps.indexOf(ts) - 1];
      ts.slide_index = prevTs?.slide_index ?? 0;
    }
  }
  console.log('🗂️  slide_index 映射完成:');
  const slideMap = {};
  for (const ts of timestamps) {
    if (!slideMap[ts.slide_index]) slideMap[ts.slide_index] = [];
    slideMap[ts.slide_index].push(ts.text.substring(0, 15) + '...');
  }
  for (const [idx, texts] of Object.entries(slideMap)) {
    console.log(`   Slide ${idx}: ${texts.join(' | ')}`);
  }
} else {
  console.warn('⚠️  未找到 script.txt，无法计算 slide_index，幻灯片将不会切换');
}

// ── 准备 public/ ──
mkdirSync(publicDir, { recursive: true });
mkdirSync(outputDir, { recursive: true });

// 复制音频到 public/ (Remotion staticFile 需要)
copyFileSync(audioPath, join(publicDir, 'audio.wav'));
console.log('🔊 音频已复制到 public/audio.wav');

// ── 构建 props ──
const props = {
  slides: slides.slides || slides,
  timestamps,
  audioUrl: '/public/audio.wav',  // staticFile('audio.wav') 在渲染时会解析
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

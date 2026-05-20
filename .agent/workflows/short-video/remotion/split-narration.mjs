#!/usr/bin/env node
/**
 * split-narration.mjs — 把 storyline.md 台词中的长行按标点拆分
 * 
 * 规则: 遇到 ，。！？；： 就换行，标点留在前一行末尾
 * 仅处理 **台词**: 块中的行
 * 
 * 用法: node split-narration.mjs <storyline.md路径>
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve } from 'path';

const filePath = resolve(process.argv[2]);
console.log(`📄 处理文件: ${filePath}`);

const content = readFileSync(filePath, 'utf-8');
const lines = content.split(/\r?\n/);

let inNarration = false;
const result = [];

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];

  // 检测 **台词**: 块的开始
  if (/^\*\*(?:台词|Narration)\*\*:/.test(line.trim())) {
    inNarration = true;
    result.push(line);
    continue;
  }

  // 检测台词块的结束: 遇到 --- 或 ** 开头的新字段或 ## 标题
  if (inNarration && (
    /^---$/.test(line.trim()) ||
    /^\*\*\w/.test(line.trim()) ||
    /^##\s/.test(line.trim()) ||
    line.trim() === ''
  )) {
    inNarration = false;
    result.push(line);
    continue;
  }

  if (inNarration && line.trim()) {
    // 按中文标点拆分，标点保留在前一段末尾
    const splits = splitAtPunctuation(line.trim());
    for (const seg of splits) {
      result.push(seg);
    }
  } else {
    result.push(line);
  }
}

// 保持原始换行风格
const newContent = result.join('\r\n');
writeFileSync(filePath, newContent, 'utf-8');

const originalNarrationLines = content.split(/\r?\n/).filter(l => {
  return l.trim() && !/^\*\*/.test(l.trim()) && !/^##/.test(l.trim()) && !/^---/.test(l.trim());
}).length;

console.log(`✅ 处理完成, ${result.length} 行 (原 ${lines.length} 行)`);

/**
 * 按中文标点拆分一行文本
 * 标点 ，。！？；： 留在前一段末尾
 * 跳过过短片段 (< 4 字)
 */
function splitAtPunctuation(text) {
  // 匹配: 至少1个字符 + 标点
  const segments = [];
  // 使用正则按标点切分，保留标点
  const parts = text.split(/(?<=[，。！？；：])/);
  
  // 合并过短的片段
  let buffer = '';
  for (const part of parts) {
    buffer += part;
    // 如果 buffer 以标点结尾且长度足够 (>= 6 字符，约3个中文字)，输出
    if (/[，。！？；：]$/.test(buffer) && buffer.length >= 6) {
      segments.push(buffer);
      buffer = '';
    }
  }
  // 剩余内容
  if (buffer) {
    if (segments.length > 0 && buffer.length < 6) {
      // 太短就并入上一段
      segments[segments.length - 1] += buffer;
    } else {
      segments.push(buffer);
    }
  }
  
  return segments.length > 0 ? segments : [text];
}

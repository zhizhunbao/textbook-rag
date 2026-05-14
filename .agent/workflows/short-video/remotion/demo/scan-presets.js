/**
 * scan-presets.js — 扫描 data/short-videos 目录，生成 presets.json
 * 
 * 用法: node scan-presets.js
 * 输出: slides/presets.json
 * 
 * presets.json 格式:
 * [
 *   { "id": "pnp-ep1", "label": "PNP EP1", "file": "../../data/short-videos/pnp/pnp-ep1/storyline.md" },
 *   ...
 * ]
 */
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.resolve(__dirname, '../../data/short-videos');
const OUT_FILE = path.join(__dirname, 'slides', 'presets.json');

function scanStorylines(dir, basePath = '') {
  const results = [];
  if (!fs.existsSync(dir)) {
    console.error(`❌ 目录不存在: ${dir}`);
    return results;
  }

  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...scanStorylines(fullPath, path.join(basePath, entry.name)));
    } else if (entry.name === 'storyline.md') {
      // 读取标题
      const content = fs.readFileSync(fullPath, 'utf-8');
      const h1 = content.match(/^# (.+)/m);
      const title = h1 ? h1[1].replace(/[—–\-]+.*$/, '').trim() : basePath;

      // 生成相对路径 (从 demo/ 到 data/short-videos/...)
      const relPath = path.relative(__dirname, fullPath).replace(/\\/g, '/');

      const id = basePath.replace(/[\\/]/g, '-').replace(/^-|-$/g, '') || 'root';
      results.push({
        id,
        label: title.slice(0, 20),
        file: relPath,
      });
    }
  }
  return results;
}

// 确保输出目录存在
const outDir = path.dirname(OUT_FILE);
if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

const presets = scanStorylines(DATA_DIR);

// 追加 demo 预设（slides/ 目录下的 demo-*.md）
const slidesDir = path.join(__dirname, 'slides');
if (fs.existsSync(slidesDir)) {
  const demoFiles = fs.readdirSync(slidesDir).filter(f => f.startsWith('demo-') && f.endsWith('.md'));
  for (const f of demoFiles) {
    const content = fs.readFileSync(path.join(slidesDir, f), 'utf-8');
    const h1 = content.match(/^# (.+)/m);
    const title = h1 ? h1[1].trim().slice(0, 20) : f.replace('.md', '');
    presets.push({
      id: `demo-${f.replace('.md', '').replace('demo-', '')}`,
      label: `📦 ${title}`,
      file: `slides/${f}`,
      format: 'slides', // 标记为旧格式
    });
  }
}

fs.writeFileSync(OUT_FILE, JSON.stringify(presets, null, 2), 'utf-8');
console.log(`✅ 已生成 ${OUT_FILE}`);
console.log(`   共 ${presets.length} 个预设:`);
presets.forEach(p => console.log(`   - [${p.id}] ${p.label} → ${p.file}`));

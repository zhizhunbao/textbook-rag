/**
 * 字体加载 — 大博主风格
 *
 * 字体方案:
 *   数字/英文标题: Montserrat Black (900) — 几何感强，数字醒目
 *   中文标题:     Noto Sans SC Black (900) — 笔画饱满，力量感
 *   中文正文:     Noto Sans SC Medium (500) — 清晰易读
 *   字幕:        Noto Sans SC Bold (700) — 醒目但不抢幻灯片
 *
 * 通过 Google Fonts CDN 加载，Remotion 渲染时 Chromium 会自动下载
 */

import { continueRender, delayRender, staticFile } from 'remotion';

const GOOGLE_FONTS_CSS = [
  // Montserrat: 600(SemiBold), 700(Bold), 800(ExtraBold), 900(Black)
  'https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800;900&display=swap',
  // Noto Sans SC: 400(Regular), 500(Medium), 700(Bold), 900(Black)
  'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap',
];

let fontsLoaded = false;

/**
 * 在组件中调用以确保字体已加载
 * Remotion 的 delayRender/continueRender 确保渲染前字体就绪
 */
export function ensureFontsLoaded(): void {
  if (fontsLoaded) return;
  fontsLoaded = true;

  if (typeof document === 'undefined') return;

  // 使用 delayRender 阻止渲染，直到字体全部加载完成
  const waitForFonts = delayRender('Waiting for Google Fonts to load');

  let linksToLoad = 0;
  let linksLoaded = 0;

  const checkAllLoaded = () => {
    if (linksLoaded >= linksToLoad) {
      // 所有 CSS 链接已加载，再等 document.fonts.ready 确保字体文件也就绪
      document.fonts.ready.then(() => {
        continueRender(waitForFonts);
      });
    }
  };

  for (const url of GOOGLE_FONTS_CSS) {
    // 避免重复插入
    if (document.querySelector(`link[href="${url}"]`)) continue;

    linksToLoad++;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = url;
    link.onload = () => {
      linksLoaded++;
      checkAllLoaded();
    };
    link.onerror = () => {
      // 即使加载失败也继续渲染，避免永久卡死
      console.warn(`Failed to load font CSS: ${url}`);
      linksLoaded++;
      checkAllLoaded();
    };
    document.head.appendChild(link);
  }

  // 如果所有链接都已经存在（重复调用场景），直接放行
  if (linksToLoad === 0) {
    document.fonts.ready.then(() => {
      continueRender(waitForFonts);
    });
  }
}

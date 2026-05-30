import React from 'react';
import { staticFile, useCurrentFrame, interpolate } from 'remotion';
import type { ThemeConfig } from '../theme';
import { getBaseStyles } from '../theme';
import type { RevealState, CropImage } from '../types';

/**
 * 证据截图页 — 固定框居中铺满
 *
 * 布局:
 *   ┌─────────────────────────────┐
 *   │       Title (居中)           │  ~88px
 *   ├─────────────────────────────┤
 *   │  ┌───────────────────────┐  │
 *   │  │                       │  │
 *   │  │  bbox 内容铺满白色框   │  │
 *   │  │  (类似表格展示)        │  │
 *   │  │                       │  │
 *   │  └───────────────────────┘  │
 *   └─────────────────────────────┘
 *
 * 策略:
 *   - 标题在框体上方居中
 *   - 固定白色圆角框居中, bbox 区域裁切后铺满框体
 *   - 台词切换时切到新 bbox 位置
 *   - 不同截图之间 opacity 过渡
 */
export const EvidenceSlide: React.FC<{
  title: string;
  cropImages: CropImage[];
  theme: ThemeConfig;
  reveal: RevealState;
}> = ({ title, cropImages, theme: t, reveal }) => {
  const styles = getBaseStyles(t);
  const hasImages = cropImages.length > 0;

  // ── 排序并确定当前活跃截图 ──
  const sorted = [...cropImages].sort((a, b) => a.triggerLine - b.triggerLine);
  let activeIdx = 0;
  for (let i = sorted.length - 1; i >= 0; i--) {
    if (reveal.spokenLines >= sorted[i].triggerLine) {
      activeIdx = i;
      break;
    }
  }

  // ── 布局常量 (与 ContentSlide 对齐: padding '60px 80px 24px') ──
  const PAD_TOP = 60;
  const PAD_X = 80;
  const PAD_BOTTOM = 24;
  const HEADING_MB = 28;       // styles.heading.marginBottom
  const HEADING_LINE = 68;     // fontSize 56 * lineHeight 1.2
  const TITLE_TOTAL = PAD_TOP + HEADING_LINE + HEADING_MB;
  const MAX_W = t.width - PAD_X * 2;    // 1760
  const MAX_H = t.slideHeight - TITLE_TOTAL - PAD_BOTTOM;

  // ── 框体自适应: 根据活跃 bbox 的宽高比调整框体尺寸 ──
  const activeCrop = sorted[activeIdx];
  const activePageW = activeCrop?.pageSize?.[0] || 960;
  const activePageH = activeCrop?.pageSize?.[1] || 792;
  const vis = getVisibleBounds(activeCrop, activePageW, activePageH);
  const visW = vis.vx2 - vis.vx1;
  const visH = vis.vy2 - vis.vy1;
  const visAR = visW / visH;

  let FRAME_W: number, FRAME_H: number;
  if (visAR > MAX_W / MAX_H) {
    // 内容偏宽 — 填满宽度
    FRAME_W = MAX_W;
    FRAME_H = MAX_W / visAR;
  } else {
    // 内容偏高 — 填满高度
    FRAME_H = MAX_H;
    FRAME_W = MAX_H * visAR;
  }

  // ── 最小尺寸约束: 防止极端宽高比导致细条框体 ──
  const MIN_FRAME_H = MAX_H * 0.35;  // 框体最小高度: 可用高度的 35%
  const MIN_FRAME_W = MAX_W * 0.45;  // 框体最小宽度: 可用宽度的 45%
  if (FRAME_H < MIN_FRAME_H) {
    FRAME_H = MIN_FRAME_H;
    FRAME_W = Math.min(MAX_W, FRAME_H * visAR);
  }
  if (FRAME_W < MIN_FRAME_W) {
    FRAME_W = MIN_FRAME_W;
    FRAME_H = Math.min(MAX_H, FRAME_W / visAR);
  }

  const groups = groupBySrc(sorted);

  return (
    <div style={{
      ...styles.slideArea,
      justifyContent: 'flex-start',
      // 保持默认 padding: '60px 80px 24px' 与 ContentSlide 一致
    }}>
      {/* ── 标题 — 位置与引用来源页一致 ── */}
      <h2 style={{
        ...styles.heading,
        opacity: reveal.spokenLines > 0 ? 1 : 0.3,
      }}>
        {title}
      </h2>

      {/* ── 自适应框体 — 白色圆角, 宽高比匹配内容 ── */}
      {hasImages && (
        <div style={{
          width: FRAME_W,
          height: FRAME_H,
          margin: '0 auto',
          position: 'relative',
          overflow: 'hidden',
          borderRadius: 12,
          background: 'rgba(255, 255, 255, 0.97)',
          boxShadow: '0 4px 40px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.08)',
        }}>
          {groups.map((group) => {
            const isGroupActive = group.crops.some((c) => {
              return sorted.indexOf(c) === activeIdx;
            });
            return (
              <FramedImage
                key={group.src}
                src={group.src}
                crops={group.crops}
                allSorted={sorted}
                activeIdx={activeIdx}
                isActive={isGroupActive}
                frameW={FRAME_W}
                frameH={FRAME_H}
                reveal={reveal}
              />
            );
          })}
        </div>
      )}

      {/* ── 无图片时标题居中 ── */}
      {!hasImages && (
        <div style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
        }} />
      )}
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
 * FramedImage — 裁切 bbox 铺满固定框体
 * ══════════════════════════════════════════════════════════════ */
const FramedImage: React.FC<{
  src: string;
  crops: CropImage[];
  allSorted: CropImage[];
  activeIdx: number;
  isActive: boolean;
  frameW: number;
  frameH: number;
  reveal: RevealState;
}> = ({ src, crops, allSorted, activeIdx, isActive, frameW, frameH, reveal }) => {
  const frame = useCurrentFrame();

  // ── crossfade: 不同截图之间平滑过渡 ──
  const prevActiveRef = React.useRef(isActive);
  const transitionFrameRef = React.useRef(0);

  if (isActive !== prevActiveRef.current) {
    transitionFrameRef.current = frame;
    prevActiveRef.current = isActive;
  }

  const FADE_FRAMES = 4;
  const framesSinceChange = frame - transitionFrameRef.current;
  let opacity: number;
  if (isActive) {
    opacity = interpolate(framesSinceChange, [0, FADE_FRAMES], [0.5, 1], { extrapolateRight: 'clamp' });
  } else {
    opacity = interpolate(framesSinceChange, [0, FADE_FRAMES], [1, 0], { extrapolateRight: 'clamp' });
  }

  // ── 当前活跃 crop ──
  let localActiveIdx = 0;
  for (let i = crops.length - 1; i >= 0; i--) {
    const globalIdx = allSorted.indexOf(crops[i]);
    if (globalIdx <= activeIdx && reveal.spokenLines >= crops[i].triggerLine) {
      localActiveIdx = i;
      break;
    }
  }

  const activeCrop = crops[localActiveIdx];
  const pageW = activeCrop.pageSize?.[0] || 960;
  const pageH = activeCrop.pageSize?.[1] || 792;

  // ── 计算裁切和定位 ──
  const { imgW, imgH, left, top } = computeFrameFit(
    activeCrop, pageW, pageH, frameW, frameH,
  );

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      left: 0,
      width: frameW,
      height: frameH,
      overflow: 'hidden',
      opacity,
    }}>
      <img
        src={staticFile(src)}
        style={{
          position: 'absolute',
          left,
          top,
          width: imgW,
          height: imgH,
          display: 'block',
        }}
      />
    </div>
  );
};

/* ══════════════════════════════════════════════════════════════
 * 工具函数
 * ══════════════════════════════════════════════════════════════ */

function groupBySrc(crops: CropImage[]): { src: string; crops: CropImage[] }[] {
  const map = new Map<string, CropImage[]>();
  for (const c of crops) {
    const list = map.get(c.src) || [];
    list.push(c);
    map.set(c.src, list);
  }
  return Array.from(map.entries()).map(([src, crops]) => ({ src, crops }));
}

/**
 * 计算可见区域边界 (bbox + 自适应 padding)
 * 共享给 EvidenceSlide (算框体尺寸) 和 computeFrameFit (算定位)
 *
 * 根据 bbox 宽高比自适应 padding:
 *   - 极宽内容 (AR>3): 增加垂直 padding，避免框体变成细条
 *   - 偏宽内容 (AR>2): 适度增加垂直 padding
 *   - 极高内容 (AR<0.5): 增加水平 padding
 *   - 正常内容: 对称 5% padding
 */
function getVisibleBounds(
  crop: CropImage | undefined,
  pageW: number,
  pageH: number,
): { vx1: number; vy1: number; vx2: number; vy2: number } {
  if (!crop?.bbox) {
    return { vx1: 0, vy1: 0, vx2: pageW, vy2: pageH };
  }

  const [x1, y1, x2, y2] = crop.bbox;
  const bboxW = x2 - x1;
  const bboxH = y2 - y1;
  const ar = bboxW / Math.max(1, bboxH);

  // 自适应 padding: 短边方向加更多呼吸空间
  let padX: number, padY: number;
  if (ar > 3) {
    // 极宽 (表格/段落): 垂直大量 padding
    padX = bboxW * 0.03;
    padY = bboxH * 0.20;
  } else if (ar > 2) {
    // 偏宽: 垂直适度 padding
    padX = bboxW * 0.04;
    padY = bboxH * 0.10;
  } else if (ar < 0.5) {
    // 极高 (侧边栏): 水平大量 padding
    padX = bboxW * 0.20;
    padY = bboxH * 0.03;
  } else {
    // 正常: 对称 padding
    padX = bboxW * 0.05;
    padY = bboxH * 0.05;
  }

  return {
    vx1: Math.max(0, x1 - padX),
    vy1: Math.max(0, y1 - padY),
    vx2: Math.min(pageW, x2 + padX),
    vy2: Math.min(pageH, y2 + padY),
  };
}

/**
 * 计算图片尺寸和位置，使可见区域铺满框体
 */
function computeFrameFit(
  crop: CropImage,
  pageW: number,
  pageH: number,
  frameW: number,
  frameH: number,
): { imgW: number; imgH: number; left: number; top: number } {
  const vis = getVisibleBounds(crop, pageW, pageH);
  const vw = vis.vx2 - vis.vx1;
  const vh = vis.vy2 - vis.vy1;

  // 缩放: 可见区域铺满框体
  const scale = Math.min(frameW / vw, frameH / vh);
  const imgW = pageW * scale;
  const imgH = pageH * scale;

  // 定位: 可见区域中心对准框体中心
  const vcx = (vis.vx1 + vis.vx2) / 2 * scale;
  const vcy = (vis.vy1 + vis.vy2) / 2 * scale;
  const left = frameW / 2 - vcx;
  const top = frameH / 2 - vcy;

  return { imgW, imgH, left, top };
}

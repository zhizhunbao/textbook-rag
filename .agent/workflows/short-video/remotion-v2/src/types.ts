/* ── 短视频 v2 数据类型 ── */

/** 单张幻灯片的数据 */
export interface SlideData {
  type: 'cover' | 'argument' | 'evidence' | 'summary' | 'cta' | 'preview' | 'highlight' | 'citation';
  title: string;
  subtitle?: string;
  hookNumber?: string;
  hookUnit?: string;
  table?: {
    headers: string[];
    rows: string[][];
  };
  points?: string[];
  content?: string;
  citation?: string;
  source: string;
  /** 证据截图列表 (render.mjs 从 document_map.json 注入) */
  cropImages?: CropImage[];
}

/** 证据截图 — 整页 PNG + 高亮 bbox (不裁剪) */
export interface CropImage {
  /** 整页 PNG 路径 (相对于 public/) */
  src: string;
  /** 第几句台词时显示此截图 (1-based) */
  triggerLine: number;
  /** 来源标签 (如 "IRCC官网") */
  sourceLabel?: string;
  /** 高亮框 bbox [x1, y1, x2, y2] — PDF 坐标 (points) */
  bbox?: [number, number, number, number];
  /** 高亮 section 范围 [top, bottom] — PDF 坐标 (points) */
  sectionBounds?: [number, number];
  /** 页面尺寸 [width, height] — PDF 坐标 (points) */
  pageSize?: [number, number];
}

/** synthesize.py 输出的 timestamps.json 中的每条记录 */
export interface TimestampEntry {
  index: number;
  line?: number;
  text: string;
  start: number;
  end: number;
  /** 对应幻灯片索引 — 由 render.mjs 在构建时注入 */
  slide_index?: number;
  has_pipe?: boolean;
}

/** 章节时间轴数据 */
export interface ChapterInfo {
  title: string;
  startSec: number;
  slideIndex: number;
}

/** 传递给 Video 组件的 props */
export interface VideoProps {
  slides: SlideData[];
  timestamps: TimestampEntry[];
  audioUrl: string;
  chapters?: ChapterInfo[];
  themeName?: string;
}

/** 分词后的单个 token */
export interface WordToken {
  text: string;
  index: number;
}

/**
 * 每个 slide 的揭示步骤信息
 * 由 ShortVideo 计算，传递给子组件
 */
export interface RevealState {
  /** 当前 slide 内已讲到的台词句数 (0 = 刚切到这页，还没开始讲) */
  spokenLines: number;
  /** 当前 slide 的总台词句数 */
  totalLines: number;
  /** 当前进度 0~1 */
  progress: number;
  /** 当前正在播放的句子在 slide 内的索引 (0-based) */
  activeLineIndex: number;
}

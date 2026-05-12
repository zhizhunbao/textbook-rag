/* ── 数据类型定义 ── */

/** 单张幻灯片的数据 */
export interface SlideData {
  type: 'cover' | 'argument' | 'evidence' | 'summary' | 'cta' | 'preview';
  title: string;
  subtitle?: string;
  /** 表格数据（argument / evidence 页） */
  table?: {
    headers: string[];
    rows: string[][];
  };
  /** 列表要点（summary 页） */
  points?: string[];
  /** 正文内容（cta / preview 页） */
  content?: string;
  /** 官方英文引用原文 */
  citation?: string;
  /** 来源 URL 水印 */
  source: string;
}

/** slides.json 的完整结构 */
export interface SlidesConfig {
  meta: {
    title: string;
    author?: string;
  };
  slides: SlideData[];
}

/** synthesize.py 输出的 timestamps.json 中的每条记录 */
export interface TimestampEntry {
  /** 句子序号 (1-based) */
  index: number;
  /** 旧字段兼容 */
  line?: number;
  text: string;
  /** 开始时间（秒） */
  start: number;
  /** 结束时间（秒） */
  end: number;
  /** 对应幻灯片索引 — 由 render.mjs 在构建时注入 */
  slide_index?: number;
  has_pipe?: boolean;
}

/** 传递给 Video 组件的 props */
export interface VideoProps {
  slides: SlideData[];
  timestamps: TimestampEntry[];
  audioUrl: string;
}

/** 分词后的单个 token（用于 TikTok 字幕高亮） */
export interface WordToken {
  text: string;
  /** 在句子中的索引 */
  index: number;
}

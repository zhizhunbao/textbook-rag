/**
 * /live — WeChat Live QA Demo route entry.
 *
 * G7-03: Full-screen live demo page for "程序员聊留学移民" broadcast.
 * Uses `live-study-immigration` hybrid persona by default.
 */

import LiveQAPage from './LiveQAPage'

export const metadata = {
  title: '直播问答 — 程序员聊留学移民 | ConsultRAG',
  description: '微信直播 AI 实时问答演示 — 基于 ConsultRAG 知识库的留学移民专业回答',
}

export default function LiveRoute() {
  return <LiveQAPage />
}

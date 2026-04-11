import React from 'react'

/**
 * Root layout — 仅做透传
 * 每个路由组 (app) / (payload) 各自提供 <html><body>
 * 这是 Payload 3.x 官方推荐的结构
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children
}

/**
 * GET /api/pipeline-preview?bookId={engineBookId}
 *
 * Proxies to Engine's /engine/pipeline-preview/{bookId} endpoint
 * which returns real input/output data for each pipeline stage.
 *
 * 代理到 Engine 的 pipeline-preview 端点，返回每个 Pipeline 阶段的
 * 真实输入/输出数据样本。
 */

import { NextRequest, NextResponse } from 'next/server'

const ENGINE = process.env.NEXT_PUBLIC_ENGINE_URL || 'http://localhost:8000'

export async function GET(req: NextRequest) {
  const bookId = req.nextUrl.searchParams.get('bookId')
  if (!bookId) {
    return NextResponse.json({ error: 'bookId is required' }, { status: 400 })
  }

  try {
    // Proxy to Engine's pipeline-preview endpoint
    const engineResp = await fetch(
      `${ENGINE}/engine/pipeline-preview/${encodeURIComponent(bookId)}`,
      { cache: 'no-store' },
    )

    if (!engineResp.ok) {
      const body = await engineResp.text()
      return NextResponse.json(
        { error: `Engine error: ${engineResp.status} ${body}` },
        { status: engineResp.status },
      )
    }

    const data = await engineResp.json()
    return NextResponse.json(data)
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err)
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

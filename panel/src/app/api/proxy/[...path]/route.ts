import { NextRequest, NextResponse } from 'next/server'

const API_BASE = 'http://localhost:8000'

async function handler(req: NextRequest, { params }: { params: { path: string[] } }) {
  const path = params.path.join('/')
  const url = `${API_BASE}/${path}${req.nextUrl.search}`
  
  const headers: Record<string, string> = {}
  req.headers.forEach((v, k) => {
    if (!['host', 'connection'].includes(k)) headers[k] = v
  })

  const res = await fetch(url, {
    method: req.method,
    headers,
    body: ['GET', 'HEAD'].includes(req.method) ? undefined : await req.text(),
  })

  const data = await res.text()
  return new NextResponse(data, {
    status: res.status,
    headers: { 'content-type': res.headers.get('content-type') || 'application/json' },
  })
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const DELETE = handler

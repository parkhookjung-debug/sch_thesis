import express from 'express'
import { readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createProxyMiddleware } from 'http-proxy-middleware'
import { renderPage } from './lib/render.mjs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const repoRoot = join(__dirname, '..')
const sitePath = join(__dirname, 'content', 'site.json')
const publicDir = join(__dirname, 'public')
const distDir = join(repoRoot, 'frontend', 'dist')

const WEB_SERVER_BUILD = 'vite-spa-proxy'

const app = express()
const port = Number(process.env.PORT || 4173)
const disableProxy = String(process.env.DISABLE_BACKEND_PROXY || '') === '1'
const backend = disableProxy
  ? ''
  : (process.env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

const hasDist = existsSync(join(distDir, 'index.html'))

function loadSite() {
  const raw = readFileSync(sitePath, 'utf8')
  return JSON.parse(raw)
}

function backendProxy() {
  const msg =
    'FastAPI 백엔드(기본 http://127.0.0.1:8000)에 연결할 수 없습니다. 프로젝트 루트에서 python main.py를 실행한 뒤 다시 시도하세요.'
  /**
   * Express `app.use('/api', proxy)` 는 내부에서 `req.url` 의 `/api` 접두사를 제거한다.
   * 그 상태로 프록시하면 백엔드는 `/recommend` 만 받게 되고, FastAPI는 SPA 폴백으로 HTML을 200에 돌려준다.
   * 루트에 한 번만 마운트하고 pathFilter 로 경로를 고르면 `/api/recommend` 가 그대로 전달된다.
   */
  return createProxyMiddleware({
    target: backend,
    changeOrigin: true,
    timeout: 120_000,
    proxyTimeout: 120_000,
    pathFilter: (pathname) =>
      pathname.startsWith('/api') ||
      pathname.startsWith('/docs') ||
      pathname === '/openapi.json' ||
      pathname.startsWith('/redoc') ||
      pathname.startsWith('/legacy'),
    on: {
      error(_err, req, res) {
        const out = res
        if (!out || typeof out.writeHead !== 'function') {
          console.error('[proxy]', req?.method, req?.url, _err?.message || _err)
          return
        }
        if (out.headersSent) {
          console.error('[proxy]', req?.method, req?.url, _err?.message || _err)
          return
        }
        out.writeHead(503, { 'Content-Type': 'application/json; charset=utf-8' })
        out.end(JSON.stringify({ detail: msg }))
      },
    },
  })
}

if (backend) {
  app.use(backendProxy())
}

app.use('/marketing', express.static(publicDir, { index: false, fallthrough: true }))

async function probeBackendReachable() {
  if (!backend) return null
  try {
    const ac = new AbortController()
    const to = setTimeout(() => ac.abort(), 1500)
    const r = await fetch(`${backend}/openapi.json`, { signal: ac.signal })
    clearTimeout(to)
    return r.ok
  } catch {
    return false
  }
}

app.get('/health', async (_req, res) => {
  const backendReachable = await probeBackendReachable()
  res.json({
    ok: true,
    build: WEB_SERVER_BUILD,
    backend: backend || null,
    backendProxy: Boolean(backend),
    backendReachable,
    viteDist: hasDist,
    distPath: hasDist ? distDir : null,
  })
})

app.get('/about', (_req, res) => {
  try {
    const doc = loadSite()
    res.type('html').send(renderPage(doc, { assetBase: '/marketing' }))
  } catch (e) {
    res.status(500).type('text').send(String(e?.message || e))
  }
})

if (hasDist) {
  app.use(
    express.static(distDir, {
      index: 'index.html',
      fallthrough: true,
    })
  )
  app.get('*', (req, res, next) => {
    if (req.method !== 'GET') return next()
    res.sendFile(join(distDir, 'index.html'), (err) => {
      if (err) next(err)
    })
  })
} else {
  app.get('/', (_req, res) => {
    res
      .status(503)
      .type('html')
      .send(
        `<!DOCTYPE html><html lang="ko"><meta charset="utf-8"/><title>빌드 필요</title>
<body style="font-family:system-ui;padding:1.5rem;max-width:36rem">
  <h1>frontend/dist 없음</h1>
  <p>React 앱을 빌드한 뒤 다시 <code>npm start</code> 하세요.</p>
  <pre style="background:#f4f4f5;padding:1rem;border-radius:8px">cd frontend
npm install
npm run build</pre>
  <p>백엔드 API는 <code>python main.py</code> (기본 8000) 가 떠 있어야 합니다.</p>
  <p><a href="/about">프로젝트 소개(정적)</a> · <a href="/health">/health</a></p>
</body></html>`
      )
  })
}

app.listen(port, () => {
  console.log(`web (Vite UI + API 프록시) http://127.0.0.1:${port}/`)
  if (backend) {
    console.log(`  → 백엔드 ${backend} (/api, /docs, …)`)
    console.log('  → 추천·코스는 FastAPI가 떠 있어야 합니다: python main.py')
  }
  if (!hasDist) console.warn('[web] frontend/dist 없음 — 빌드 후 전체 UI를 씁니다.')
})

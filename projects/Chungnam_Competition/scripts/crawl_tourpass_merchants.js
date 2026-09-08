/**
 * 네이버 스마트스토어 상품 상세 1회 로딩 후 텍스트·이미지 수집 → Python OCR/파서 호출
 * 사용: npm run crawl:tourpass
 *
 * Playwright 1.49+: headless shell 대신 이미 받은 full Chromium 사용(설치 부분 완료 시).
 */
if (!process.env.PLAYWRIGHT_CHROMIUM_USE_HEADLESS_SHELL) {
  process.env.PLAYWRIGHT_CHROMIUM_USE_HEADLESS_SHELL = '0'
}
const fs = require('fs')
const os = require('os')
const path = require('path')
const { spawnSync } = require('child_process')

const { chromium } = require('playwright')

/** ms-playwright에 내려받은 full Chromium 실행 파일 (headless shell 없을 때 대비) */
function resolveLocalPlaywrightChromiumExe() {
  const base = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local')
  const root = path.join(base, 'ms-playwright')
  if (!fs.existsSync(root)) return null
  let best = null
  for (const d of fs.readdirSync(root)) {
    if (!/^chromium-\d+$/.test(d)) continue
    const exe = path.join(root, d, 'chrome-win64', 'chrome.exe')
    if (fs.existsSync(exe)) {
      const num = parseInt(d.replace('chromium-', ''), 10)
      if (!Number.isNaN(num) && (!best || num > best.n)) best = { n: num, exe }
    }
  }
  return best?.exe ?? null
}

const ROOT = path.join(__dirname, '..')
const OUTPUT_DIR = path.join(ROOT, 'output')
const IMAGES_DIR = path.join(OUTPUT_DIR, 'images')
const SOURCE_URL =
  process.env.TOURPASS_PRODUCT_URL ||
  'https://smartstore.naver.com/lscompany01/products/10218084169'

const HTML_TEXT_DUMP = path.join(OUTPUT_DIR, '_html_detail_text.txt')
const PYTHON_SCRIPT = path.join(__dirname, 'ocr_tourpass_merchants.py')

const URL_HINT =
  /product|detail|merchant|tour|pass|chungnam|smartstore|shop\d+|cdn|cafe|naver|phinf/i

const SKIP_SMALL_W = 320
const SKIP_SMALL_H = 240
const MAX_AREA_FOR_TINY = SKIP_SMALL_W * SKIP_SMALL_H

function ensureDirs() {
  fs.mkdirSync(IMAGES_DIR, { recursive: true })
  fs.mkdirSync(OUTPUT_DIR, { recursive: true })
}

function absolutizeUrl(pageUrl, src) {
  if (!src || typeof src !== 'string') return null
  const s = src.trim().split(/\s+/)[0]
  if (!s || s.startsWith('data:')) return null
  try {
    return new URL(s, pageUrl).href
  } catch {
    return null
  }
}

function isLikelyDetailUrl(href) {
  if (!href) return false
  const lower = href.toLowerCase()
  if (lower.includes('ico') || lower.includes('favicon')) return false
  if (/phinf\.pstatic|shopv|shopping\.naver|nshop|naver\.net|pstatic\.net/.test(lower))
    return true
  if (URL_HINT.test(lower)) return true
  if (/\.(jpe?g|png|webp)(\?|$)/i.test(lower)) return true
  return false
}

/**
 * @param {import('playwright').Page} page
 */
async function collectDetailText(page) {
  const blocks = []
  try {
    blocks.push('--- main frame ---\n')
    const main = await page.locator('body').innerText({ timeout: 15000 }).catch(() => '')
    blocks.push(main || '')
  } catch {
    blocks.push('')
  }

  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue
    try {
      const u = frame.url() || ''
      if (!u || u === 'about:blank') continue
      const t = await frame.locator('body').innerText({ timeout: 3000 }).catch(() => '')
      if (t && t.length > 50) {
        blocks.push(`\n--- frame: ${u.slice(0, 120)} ---\n`)
        blocks.push(t)
      }
    } catch {
      /* skip */
    }
  }
  return blocks.join('\n')
}

/**
 * @param {import('playwright').Page} page
 */
async function collectImageUrls(page) {
  const pageUrl = page.url()
  const found = new Set()

  const parsed = await page.evaluate(() => {
    const rows = []
    document.querySelectorAll('img').forEach((img) => {
      const w = img.naturalWidth || img.width || 0
      const h = img.naturalHeight || img.height || 0
      let src =
        img.currentSrc ||
        img.getAttribute('src') ||
        img.getAttribute('data-src') ||
        img.getAttribute('data-original') ||
        ''
      const srcset = img.getAttribute('srcset')
      if (srcset) {
        const first = srcset.split(',')[0]?.trim().split(/\s+/)[0]
        if (first) src = first
      }
      if (src) rows.push({ src: String(src).trim(), w, h })
    })
    document.querySelectorAll('*').forEach((el) => {
      const st = window.getComputedStyle(el)
      const bg = st.backgroundImage
      if (bg && bg !== 'none') {
        const m = /url\(["']?([^"')]+)["']?\)/.exec(bg)
        if (m && m[1]) rows.push({ src: m[1].trim(), w: 800, h: 600 })
      }
    })
    return rows
  })

  for (const obj of parsed) {
    if (!obj || !obj.src) continue
    const w = Number(obj.w) || 0
    const h = Number(obj.h) || 0
    const area = w * h
    if (w > 0 && h > 0 && area < MAX_AREA_FOR_TINY) continue
    if (w > 0 && h > 0 && (w < SKIP_SMALL_W || h < SKIP_SMALL_H)) continue

    const href = absolutizeUrl(pageUrl, obj.src)
    if (!href) continue
    if (!isLikelyDetailUrl(href)) continue
    found.add(href)
  }

  return prioritizeImageUrls([...found])
}

/** URL 우선순위: 상세·상품 이미지 먼저, 과다 요청 방지 상한 */
function prioritizeImageUrls(urls) {
  const scored = urls.map((u) => {
    let s = 0
    const l = u.toLowerCase()
    if (/product|detail|content|editor|merchandise|shop/.test(l)) s += 30
    if (/phinf\.pstatic|pstatic\.net/.test(l)) s += 15
    if (/\.png(\?|$)/.test(l)) s += 2
    return { u, s }
  })
  scored.sort((a, b) => b.s - a.s)
  const maxImages = 28
  return scored.slice(0, maxImages).map((x) => x.u)
}

async function downloadImages(context, urls) {
  const saved = []
  let idx = 0
  for (const url of urls) {
    idx += 1
    const extMatch = /\.(jpe?g|png|webp|gif)(\?|$)/i.exec(url)
    const ext = extMatch ? extMatch[1].toLowerCase().replace('jpeg', 'jpg') : 'jpg'
    const filename = `detail_${String(idx).padStart(3, '0')}.${ext}`
    const dest = path.join(IMAGES_DIR, filename)
    try {
      const res = await context.request.get(url, { timeout: 30000 })
      if (!res.ok()) {
        console.warn(`이미지 다운로드 HTTP ${res.status()}: ${url.slice(0, 80)}`)
        continue
      }
      const buf = await res.body()
      if (!buf || buf.length < 400) {
        console.warn(`이미지 용량이 너무 작아 제외: ${filename}`)
        continue
      }
      fs.writeFileSync(dest, buf)
      saved.push({ filename, url })
    } catch (e) {
      console.warn(`이미지 다운로드 실패 (${filename}): ${e.message || e}`)
    }
  }
  return saved
}

function runPythonOcr(htmlTextPath, imageManifestPath) {
  const py = process.env.PYTHON || 'python'
  const r = spawnSync(
    py,
    [
      PYTHON_SCRIPT,
      '--html-text',
      htmlTextPath,
      '--image-manifest',
      imageManifestPath,
      '--images-dir',
      IMAGES_DIR,
      '--out-raw',
      path.join(OUTPUT_DIR, 'chungnam_tourpass_merchants_raw.txt'),
      '--out-csv',
      path.join(OUTPUT_DIR, 'chungnam_tourpass_merchants.csv'),
      '--source-url',
      SOURCE_URL,
    ],
    { cwd: ROOT, stdio: 'inherit', encoding: 'utf-8', env: { ...process.env, PYTHONIOENCODING: 'utf-8' } },
  )
  if (r.error) {
    console.error('Python 실행 오류:', r.error.message)
    return r.status ?? 1
  }
  return r.status ?? 0
}

async function main() {
  ensureDirs()
  console.log('페이지 로딩(1회):', SOURCE_URL)

  let browser
  try {
    const chromeExe = resolveLocalPlaywrightChromiumExe()
    if (!chromeExe) {
      console.error(
        'Chromium 실행 파일을 찾을 수 없습니다. 다음을 실행한 뒤 다시 시도하세요:\n' +
          '  npx playwright install chromium',
      )
      process.exitCode = 1
      return
    }
    browser = await chromium.launch({
      headless: true,
      executablePath: chromeExe,
    })
    const context = await browser.newContext({
      locale: 'ko-KR',
      userAgent:
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })
    const page = await context.newPage()
    const res = await page.goto(SOURCE_URL, {
      waitUntil: 'domcontentloaded',
      timeout: 60000,
    })
    let lastStatus = res ? res.status() : 0
    let ok = res && res.ok()
    if (res && res.status() === 429) {
      console.warn('HTTP 429 — 12초 후 1회만 재시도합니다.')
      await new Promise((r) => setTimeout(r, 12000))
      const res2 = await page.goto(SOURCE_URL, {
        waitUntil: 'domcontentloaded',
        timeout: 60000,
      })
      lastStatus = res2 ? res2.status() : lastStatus
      ok = res2 && res2.ok()
    }
    if (!ok) {
      console.error(
        '페이지 접근 실패:',
        lastStatus ? `HTTP ${lastStatus}` : '응답 없음',
        '(본문이 없을 수 있으나 중간 산출물은 저장합니다)',
      )
    }
    await new Promise((r) => setTimeout(r, 5000))

    const detailText = await collectDetailText(page)
    const blocked =
      /현재 서비스 접속이 불가|접속이 불가합니다|HTTP\s*429|Too Many Requests/i.test(
        detailText,
      )
    const toWrite =
      (blocked ? '[[BLOCKED_OR_ERROR]]\n' : '') + (detailText || '')
    fs.writeFileSync(HTML_TEXT_DUMP, toWrite, 'utf8')

    const imgUrls = await collectImageUrls(page)
    let savedMeta = []
    if (imgUrls.length === 0) {
      console.warn('경고: 상세 영역에서 후보 이미지 URL을 찾지 못했습니다.')
    } else {
      savedMeta = await downloadImages(context, imgUrls)
    }

    const manifestPath = path.join(OUTPUT_DIR, '_image_manifest.json')
    fs.writeFileSync(manifestPath, JSON.stringify(savedMeta, null, 2), 'utf8')

    console.log('\n[1차] HTML 텍스트 저장:', HTML_TEXT_DUMP)
    console.log(`[2차] 다운로드한 이미지: ${savedMeta.length}개 (후보 URL ${imgUrls.length}개)\n`)

    const code = runPythonOcr(HTML_TEXT_DUMP, manifestPath)
    if (code !== 0) {
      process.exitCode = code || 1
    }
  } catch (e) {
    console.error('크롤링 실패:', e.message || e)
    process.exitCode = 1
  } finally {
    if (browser) await browser.close().catch(() => {})
  }
}

main()

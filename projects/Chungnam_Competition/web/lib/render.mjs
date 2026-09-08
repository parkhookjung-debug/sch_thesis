/**
 * site.json → HTML (기존 nodes-site/build.mjs 렌더 로직)
 */
export function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function rich(s) {
  const parts = String(s ?? '').split(/\*\*/)
  return parts.map((chunk, i) => (i % 2 === 1 ? `<strong>${esc(chunk)}</strong>` : esc(chunk))).join('')
}

function renderActions(actions) {
  return (actions || [])
    .map((a) => {
      const cls = a.primary ? 'btn primary' : 'btn ghost'
      return `<a class="${cls}" href="${esc(a.href)}">${esc(a.label)}</a>`
    })
    .join('\n')
}

function renderNav(nav) {
  return (nav || []).map((n) => `<a class="nav-link" href="${esc(n.href)}">${esc(n.label)}</a>`).join('')
}

function sectionCards(section) {
  const items = section.items || []
  return items
    .map(
      (it) => `
    <article class="card">
      <div class="card-icon" aria-hidden="true">${esc(it.icon || '·')}</div>
      <h3>${esc(it.title)}</h3>
      <p class="card-body">${rich(it.body)}</p>
    </article>`
    )
    .join('')
}

function sectionEndpoints(section) {
  const rows = (section.endpoints || [])
    .map(
      (e) => `
    <tr>
      <td class="m"><code>${esc(e.method)}</code></td>
      <td class="p"><code>${esc(e.path)}</code></td>
      <td class="d">${rich(e.desc)}</td>
    </tr>`
    )
    .join('')
  return `
  <div class="table-wrap">
    <table class="api-table">
      <thead><tr><th>메서드</th><th>경로</th><th>설명</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`
}

function sectionList(section) {
  const items = section.items || []
  return items
    .map(
      (it) => `
    <div class="list-row">
      <h3>${esc(it.title)}</h3>
      <p>${rich(it.body)}</p>
    </div>`
    )
    .join('')
}

function sectionTimeline(section) {
  const events = section.events || []
  return events
    .map(
      (e) => `
    <li>
      <strong>${esc(e.label)}</strong>
      <p>${rich(e.detail)}</p>
    </li>`
    )
    .join('')
}

function renderSection(section) {
  const id = esc(section.id || '')
  const title = esc(section.title || '')
  const sub = section.subtitle ? `<p class="section-sub">${rich(section.subtitle)}</p>` : ''
  let inner = ''
  const layout = section.layout || 'cards'
  if (layout === 'cards') {
    inner = `<div class="grid">${sectionCards(section)}</div>`
  } else if (layout === 'endpoints') {
    inner = sectionEndpoints(section)
  } else if (layout === 'list') {
    inner = `<div class="list-block">${sectionList(section)}</div>`
  } else if (layout === 'timeline') {
    inner = `<ol class="timeline">${sectionTimeline(section)}</ol>`
  } else {
    inner = `<div class="grid">${sectionCards(section)}</div>`
  }
  return `
    <section class="section" id="${id}">
      <h2 class="section-title">${title}</h2>
      ${sub}
      ${inner}
    </section>`
}

function renderFooter(footer) {
  const lines = (footer?.lines || []).map((l) => `<p>${rich(l)}</p>`).join('')
  const links = (footer?.links || [])
    .map((l) => `<a href="${esc(l.href)}">${esc(l.label)}</a>`)
    .join(' · ')
  return `
    <footer class="site-footer">
      ${lines}
      <p class="footer-links">${links}</p>
    </footer>`
}

/** @param {Record<string, unknown>} doc @param {{ assetBase?: string }} [opts] */
export function renderPage(doc, opts = {}) {
  const { meta, header, hero, sections, footer } = doc
  const sectionsHtml = (sections || []).map(renderSection).join('\n')
  const base = String(opts.assetBase || '').replace(/\/$/, '')
  const cssHref = base ? `${base}/style.css` : '/style.css'

  return `<!DOCTYPE html>
<html lang="${esc(meta?.lang || 'ko')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${esc(meta?.title)}</title>
  <meta name="description" content="${esc(meta?.description)}" />
  <link rel="stylesheet" href="${esc(cssHref)}" />
</head>
<body>
  <header class="site-header">
    <span class="brand">${esc(header?.brand || meta?.title)}</span>
    <nav class="nav" aria-label="섹션">${renderNav(header?.nav)}</nav>
  </header>
  <div class="hero-bg" id="top">
    <div class="hero">
      <p class="eyebrow">${esc(hero?.eyebrow)}</p>
      <h1>${esc(hero?.headline)}</h1>
      <p class="lead">${rich(hero?.lead)}</p>
      <div class="actions">${renderActions(hero?.actions)}</div>
    </div>
  </div>
  <div class="wrap">
    ${sectionsHtml}
    ${renderFooter(footer)}
  </div>
</body>
</html>`
}

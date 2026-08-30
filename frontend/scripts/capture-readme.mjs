import { chromium } from '@playwright/test'
import { readFile, mkdir } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDirectory = dirname(fileURLToPath(import.meta.url))
const repository = resolve(scriptDirectory, '..', '..')
const outputDirectory = join(repository, 'docs', 'images')
await mkdir(outputDirectory, { recursive: true })

const escapeHtml = (value) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')

const highlight = (line) => {
  const tokens = /(\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*')|(#.*$)|\b(from|import|def|return|if|else|for|in|with|as|try|except|raise|None|True|False)\b|\b(\d+)\b/g
  let output = ''
  let cursor = 0
  for (const match of line.matchAll(tokens)) {
    output += escapeHtml(line.slice(cursor, match.index))
    const type = match[1] ? 'string' : match[2] ? 'comment' : match[3] ? 'keyword' : 'number'
    output += '<span class="' + type + '">' + escapeHtml(match[0]) + '</span>'
    cursor = match.index + match[0].length
  }
  return output + escapeHtml(line.slice(cursor))
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 })

try {
  await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' })
  await page.getByLabel('Email').fill('admin@example.com')
  await page.getByLabel('Password').fill(process.env.E2E_PASSWORD || 'SignalGraph!2026')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.getByRole('heading', { name: 'Intelligence overview' }).waitFor()
  await page.screenshot({ path: join(outputDirectory, 'signalgraph-dashboard.png') })

  await page.getByRole('link', { name: 'Intelligence' }).click()
  await page.getByRole('heading', { name: 'Intelligence library' }).waitFor()
  await page.getByText('northstar-login.example').first().click()
  await page.getByText('Source observations').waitFor()
  await page.screenshot({ path: join(outputDirectory, 'signalgraph-provenance.png') })

  await page.getByRole('link', { name: 'Graph explorer' }).click()
  await page.getByLabel('Interactive relationship graph').waitFor()
  const startingEntity = page.getByLabel('Starting entity')
  const northstarId = await startingEntity.locator('option').filter({ hasText: 'northstar-login.example' }).getAttribute('value')
  if (!northstarId) throw new Error('Northstar graph seed was not found')
  const graphResponse = page.waitForResponse((response) => response.url().includes('/graph/' + northstarId) && response.ok())
  await startingEntity.selectOption(northstarId)
  await graphResponse
  await page.waitForTimeout(900)
  await page.screenshot({ path: join(outputDirectory, 'signalgraph-graph.png') })

  const source = await readFile(join(repository, 'backend', 'app', 'services', 'enrichment.py'), 'utf8')
  const sourceLines = source.split(/\r?\n/)
  const firstLine = sourceLines.findIndex((line) => line.startsWith('def run_job'))
  const excerpt = sourceLines.slice(firstLine, firstLine + 43)
  const rows = excerpt.map((line, index) => '<div class="line"><span class="numbering">' + String(firstLine + index + 1).padStart(3, ' ') + '</span><span class="source">' + highlight(line) + '</span></div>').join('')
  const codeHtml = [
    '<!doctype html><html><head><meta charset="utf-8"><style>',
    '*{box-sizing:border-box}body{margin:0;background:#071016;color:#dce8ed;font-family:Inter,Segoe UI,sans-serif;padding:48px}',
    '.window{height:1104px;border:1px solid #263a46;border-radius:15px;overflow:hidden;background:#0b151c;box-shadow:0 30px 90px #020608}',
    '.bar{height:78px;display:flex;align-items:center;border-bottom:1px solid #263a46;padding:0 28px;background:#0e1a22}',
    '.dots{display:flex;gap:9px;margin-right:24px}.dots i{width:12px;height:12px;border-radius:50%;display:block}.dots i:nth-child(1){background:#ef7c79}.dots i:nth-child(2){background:#f5bd68}.dots i:nth-child(3){background:#62d6c6}',
    '.path{font:600 15px ui-monospace,SFMono-Regular,Consolas,monospace;color:#a9bac4}.badge{margin-left:auto;border:1px solid #265f5b;color:#62d6c6;border-radius:999px;padding:7px 12px;font:700 11px ui-monospace,Consolas,monospace;letter-spacing:.12em}',
    '.caption{height:84px;padding:22px 30px 15px;border-bottom:1px solid #1c2c35}.caption strong{font-size:18px}.caption span{display:block;color:#76909e;font-size:13px;margin-top:5px}',
    '.code{padding:22px 0;font:14.5px/21px ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre;tab-size:4}.line{display:flex;min-height:21px}.line:hover{background:#11232d}',
    '.numbering{width:76px;text-align:right;padding-right:21px;color:#45606e;user-select:none;border-right:1px solid #182a34}.source{padding-left:24px;color:#c9d6dc}',
    '.keyword{color:#d9a7ff;font-weight:600}.string{color:#9bd596}.comment{color:#637b87;font-style:italic}.number{color:#f0bb75}',
    '</style></head><body><section class="window"><header class="bar"><span class="dots"><i></i><i></i><i></i></span><span class="path">backend/app/services/enrichment.py</span><span class="badge">SIGNALGRAPH / V1</span></header>',
    '<div class="caption"><strong>Concurrent, failure-aware enrichment</strong><span>Every collector result keeps raw evidence, provenance, and an explainable outcome.</span></div><main class="code">',
    rows,
    '</main></section></body></html>',
  ].join('')
  await page.setViewportSize({ width: 1600, height: 1200 })
  await page.setContent(codeHtml)
  await page.screenshot({ path: join(outputDirectory, 'signalgraph-enrichment-code.png') })
} finally {
  await browser.close()
}

console.log('README screenshots written to ' + outputDirectory)

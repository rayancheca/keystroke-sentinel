/**
 * Live workflow screenshot capture for Keystroke Sentinel.
 * Strategy: seed enrollment data via HTTP API (fast + stable),
 * then use Playwright only for UI navigation and screenshots.
 */

const { chromium } = require('playwright')
const path = require('path')
const http = require('http')

const BASE_URL = 'http://localhost:5173'
const API_BASE = 'http://localhost:8000'
const OUT_DIR = path.join(__dirname, '..', 'docs', 'screenshots')
const USER_ID = 'demo-alice'

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

// HTTP helper
function apiPost(endpoint, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body)
    const url = new URL(API_BASE + endpoint)
    const req = http.request(
      {
        hostname: url.hostname,
        port: url.port,
        path: url.pathname,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) },
      },
      (res) => {
        let body = ''
        res.on('data', (c) => (body += c))
        res.on('end', () => {
          if (res.statusCode >= 400) return reject(new Error(`HTTP ${res.statusCode}: ${body}`))
          resolve(JSON.parse(body))
        })
      }
    )
    req.on('error', reject)
    req.write(data)
    req.end()
  })
}

// Generate a realistic synthetic burst matching the extractor's expected shape
function makeBurst(sessionId, n) {
  const keys = 'abcdefghijklmnopqrstuvwxyz the quick brown fox'.split('')
  const events = []
  let t = Date.now() - 5000 + n * 120
  for (let i = 0; i < 20; i++) {
    const key = keys[(n * 20 + i) % keys.length]
    const dwell = 80 + Math.random() * 60          // 80–140ms natural dwell
    const flight = 60 + Math.random() * 80          // 60–140ms flight
    events.push({ key, press_time: t, release_time: t + dwell })
    t += dwell + flight
  }
  return {
    user_id: USER_ID,
    session_id: sessionId,
    events,
    wpm: 52 + Math.random() * 10,
    error_count: Math.floor(Math.random() * 2),
    word_count: 4,
  }
}

async function shot(page, n, label) {
  const file = path.join(OUT_DIR, `${String(n).padStart(2, '0')}_${label}.png`)
  await page.screenshot({ path: file, fullPage: false })
  console.log(`  [${n}] ${label}`)
}

async function typeNatural(page, selector, text, wpm = 52) {
  const msPerChar = (60 / (wpm * 5)) * 1000
  await page.focus(selector)
  for (const ch of text) {
    await page.keyboard.type(ch)
    await sleep(Math.max(30, msPerChar + (Math.random() - 0.5) * msPerChar * 0.5))
  }
}

async function main() {
  const { mkdirSync } = require('fs')
  mkdirSync(OUT_DIR, { recursive: true })

  // ── Seed enrollment via API ──────────────────────────────────────────────
  console.log('Seeding enrollment data via API…')
  await apiPost('/enrollment/start', { user_id: USER_ID })

  const sessionId = `seed-${Date.now()}`
  // 18 bursts × 20 events = 360 keystrokes (> 300 threshold)
  for (let i = 0; i < 18; i++) {
    await apiPost('/enrollment/burst', makeBurst(sessionId, i))
    process.stdout.write('.')
  }
  console.log(' done')

  // ── Launch browser ───────────────────────────────────────────────────────
  const browser = await chromium.launch({ headless: true })
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await ctx.newPage()

  // ── 1. Enrollment empty state ────────────────────────────────────────────
  console.log('\nStep 1: enrollment screen')
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  await page.waitForSelector('.enrollment__header', { timeout: 10000 })
  await sleep(500)
  await shot(page, 1, 'enrollment_empty')

  // ── 2. User ID entered ───────────────────────────────────────────────────
  console.log('Step 2: enter user ID')
  await page.fill('#user-id', USER_ID)
  await sleep(400)
  await shot(page, 2, 'enrollment_user_id_entered')

  // ── 3. Begin enrollment → typing phase (already has data via API) ────────
  console.log('Step 3: begin enrollment (data already seeded)')
  await page.click('.enrollment__btn')
  await page.waitForSelector('.enrollment__typing-area', { timeout: 10000 })
  await sleep(600)
  await shot(page, 3, 'enrollment_typing_phase')

  // Type a short sample so the screenshot shows active typing
  console.log('  Short typing sample for screenshot…')
  await typeNatural(page, '.enrollment__textarea', 'The quick brown fox jumps.', 48)
  await sleep(3000) // wait for burst to process

  await shot(page, 4, 'enrollment_typing_progress')

  // ── 4. Train classifier (button should be enabled — 360 keystrokes seeded)
  console.log('Step 4: train classifier')
  const trainBtn = page.locator('.enrollment__btn:not([disabled])', { hasText: 'Train classifier' })
  await trainBtn.waitFor({ state: 'visible', timeout: 10000 })
  await shot(page, 5, 'enrollment_ready_to_train')
  await trainBtn.click()

  // Wait for CV bars
  await page.waitForSelector('.enrollment__cv-bar', { timeout: 30000 })
  await sleep(700)
  await shot(page, 6, 'enrollment_training_complete')

  // ── 5. Live monitoring dashboard ─────────────────────────────────────────
  console.log('Step 5: enter live monitoring')
  await page.click('.enrollment__btn:has-text("Start live monitoring")')
  await page.waitForSelector('.dashboard', { timeout: 10000 })
  await sleep(1200)
  await shot(page, 7, 'dashboard_connected')

  // ── 6. Type naturally — generates scoring bursts ─────────────────────────
  console.log('Step 6: live scoring (natural typing)')
  await typeNatural(
    page,
    '.typing-pad__textarea',
    'The quick brown fox jumps over the lazy dog. Pack my box with five.',
    50
  )
  await sleep(3500) // wait for burst + WS score
  await shot(page, 8, 'dashboard_live_scoring')

  // Second burst for waveform history
  await typeNatural(
    page,
    '.typing-pad__textarea',
    'How vexingly quick daft zebras jump! Sphinx of black quartz.',
    52
  )
  await sleep(3500)
  await shot(page, 9, 'dashboard_waveform_history')

  // ── 7. Trigger anomaly ───────────────────────────────────────────────────
  console.log('Step 7: trigger anomaly (robotic burst)')
  await page.focus('.typing-pad__textarea')
  // Very uniform fast cadence — designed to look inhuman vs. the trained model
  const robotText = 'AAAAAABBBBBBCCCCCCDDDDDDEEEEEEFFFFFFGGGGGGHHHHHHIIIIII'
  for (const ch of robotText) {
    await page.keyboard.type(ch)
    await sleep(15)
  }
  await sleep(3500)

  const hasChallenge = await page.$('.challenge-overlay')
  if (hasChallenge) {
    await shot(page, 10, 'dashboard_reauth_challenge')
    console.log('  Re-auth challenge overlay captured!')
  } else {
    await shot(page, 10, 'dashboard_anomaly_score')
    console.log('  Anomaly score screenshot (overlay threshold not reached)')
  }

  await browser.close()
  console.log(`\nDone. Screenshots in docs/screenshots/`)
}

main().catch((err) => {
  console.error('\nERROR:', err.message)
  process.exit(1)
})

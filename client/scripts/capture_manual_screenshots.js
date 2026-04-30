const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..', '..');
const FIXTURE_DIR = path.join(ROOT, 'client', 'docs', 'manual-fixtures');
const OUTPUT_DIR = path.join(ROOT, 'client', 'docs', 'manual-assets');
const BASE_URL = 'http://127.0.0.1:3000/dosya/';
const CHROME_PATH = '/tmp/ms-playwright/chromium-1208/chrome-linux64/chrome';

const meta = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'meta.json'), 'utf8'));
const sessionInfo = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'session-info.json'), 'utf8'));
const adjustedSessionInfo = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'session-info-adjusted.json'), 'utf8'));
const prefectureData = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'prefecture-data.json'), 'utf8'));
const riskAtTime = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'risk-at-time.json'), 'utf8'));
const adjustedRiskAtTime = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'risk-at-time-adjusted.json'), 'utf8'));
const rainfallData = JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, 'rainfall-data.json'), 'utf8'));

fs.mkdirSync(OUTPUT_DIR, { recursive: true });

function jsonResponse(route, body) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json; charset=utf-8',
    body: JSON.stringify(body),
  });
}

async function capture() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: CHROME_PATH,
  });
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1400 },
    deviceScaleFactor: 1,
  });

  await page.route('**/production-soil-rainfall-index-with-urls', async (route) => {
    await jsonResponse(route, sessionInfo);
  });

  await page.route(`**/session/${meta.session_id}/prefecture/*`, async (route) => {
    await jsonResponse(route, prefectureData);
  });

  await page.route(`**/session/${meta.adjusted_session_id}/prefecture/*`, async (route) => {
    await jsonResponse(route, prefectureData);
  });

  await page.route(`**/session/${meta.session_id}/risk-at-time*`, async (route) => {
    await jsonResponse(route, riskAtTime);
  });

  await page.route(`**/session/${meta.adjusted_session_id}/risk-at-time*`, async (route) => {
    await jsonResponse(route, adjustedRiskAtTime);
  });

  await page.route(`**/session/${meta.session_id}/rainfall-data`, async (route) => {
    await jsonResponse(route, rainfallData);
  });

  await page.route(`**/session/${meta.adjusted_session_id}/rainfall-data`, async (route) => {
    await jsonResponse(route, rainfallData);
  });

  await page.route(`**/session/${meta.session_id}/recalculate`, async (route) => {
    await jsonResponse(route, {
      status: 'success',
      session_id: meta.adjusted_session_id,
      adjusted: true,
      ft: meta.first_ft,
      mesh_risks: adjustedRiskAtTime.mesh_risks,
      mesh_coords: adjustedRiskAtTime.mesh_coords,
    });
  });

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(OUTPUT_DIR, '01-initial-screen.png'), fullPage: true });

  await page.getByRole('button', { name: 'データを取得' }).click();
  await page.waitForSelector('text=セッションID:');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '02-loaded-screen.png'), fullPage: true });

  await page.getByRole('button', { name: '雨量調整' }).click();
  await page.waitForSelector('text=雨量調整');
  await page.waitForSelector('text=入力単位:');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '03-rainfall-modal-3hour.png'), fullPage: true });

  await page.getByRole('button', { name: '24時間合計' }).click();
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '04-rainfall-modal-24hour.png'), fullPage: true });

  const cellSelector = `td[data-area="${meta.sample_area_key}"][data-ft="${meta.sample_area_24h_ft}"] input`;
  await page.locator(cellSelector).fill('120');
  await page.getByRole('button', { name: '再計算' }).click();
  await page.waitForSelector('text=雨量調整済みデータ');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(OUTPUT_DIR, '05-adjusted-result.png'), fullPage: true });

  await browser.close();
}

capture().catch((error) => {
  console.error(error);
  process.exit(1);
});

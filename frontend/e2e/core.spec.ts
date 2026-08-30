import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Email').fill(process.env.E2E_EMAIL || 'admin@example.com')
  await page.getByLabel('Password').fill(process.env.E2E_PASSWORD || 'SignalGraph!2026')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Intelligence overview' })).toBeVisible()
})

test('analyst can inspect dashboard and intelligence provenance', async ({ page }) => {
  await expect(page.getByText('Known entities')).toBeVisible()
  await expect(page.getByText('High-risk intelligence')).toBeVisible()
  await page.getByRole('link', { name: 'Intelligence' }).click()
  await expect(page.getByRole('heading', { name: 'Intelligence library' })).toBeVisible()
  await page.getByText('northstar-login.example').first().click()
  await expect(page.getByText('Transparent risk score')).toBeVisible()
  await expect(page.getByText('Source observations')).toBeVisible()
  await page.getByRole('button', { name: 'Add evidence' }).click()
  await expect(page.getByText('Added to investigation')).toBeVisible()
})

test('analyst can pivot through the relationship graph', async ({ page }) => {
  await page.getByRole('link', { name: 'Graph explorer' }).click()
  await expect(page.getByRole('heading', { name: 'Relationship graph' })).toBeVisible()
  await expect(page.getByLabel('Interactive relationship graph')).toBeVisible()
  await expect(page.getByText(/nodes · \d+ edges/)).toBeVisible()
  await page.getByTitle('Graph filters').click()
  await expect(page.getByText('ENTITY TYPES')).toBeVisible()
  const domainFilter = page.locator('.filter-pills label').filter({ hasText: 'Domain' }).first()
  await Promise.all([
    page.waitForResponse((response) => response.url().includes('entity_type=domain') && response.ok()),
    domainFilter.click(),
  ])
})

test('analyst can open an investigation and its evidence timeline', async ({ page }) => {
  await page.getByRole('link', { name: 'Investigations' }).click()
  await expect(page.getByRole('heading', { name: 'Investigations' })).toBeVisible()
  await expect(page.getByText('Northstar credential lure').first()).toBeVisible()
  await expect(page.getByText('Linked intelligence')).toBeVisible()
  await expect(page.getByText('Certificate reuse links both domains')).toBeVisible()
  await page.getByRole('button', { name: 'Open case graph' }).click()
  await expect(page.getByText('Current investigation')).toBeVisible()
  await expect(page.getByLabel('Interactive relationship graph')).toBeVisible()
})

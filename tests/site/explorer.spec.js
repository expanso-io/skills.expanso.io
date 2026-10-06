const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test('pipeline explorer shows recorded stage data and keeps scroll on navigation', async ({ page }) => {
  await page.goto('/skill/slug-generate/');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const explorer = page.locator('.step-explorer:visible');
  await expect(explorer.getByRole('heading', { name: 'Step explorer', exact: true })).toBeVisible();
  await expect(explorer.locator('.stage-input')).toContainText('Hello World');
  await expect(explorer.locator('.stage-output')).toContainText('hello-world');
  await explorer.scrollIntoViewIfNeeded();
  const scroll = await page.locator('#skill-modal').evaluate(el => el.scrollTop);
  await page.keyboard.press('ArrowRight');
  await expect(explorer.locator('.stage-position')).toHaveText('Stage 2 of 2: log');
  expect(await page.locator('#skill-modal').evaluate(el => el.scrollTop)).toBe(scroll);
  await page.keyboard.press('ArrowLeft');
  await expect(explorer.locator('.stage-position')).toHaveText('Stage 1 of 2: mapping');
  await explorer.getByRole('button', { name: 'Next stage', exact: true }).click();
  await expect(explorer.locator('.stage-position')).toHaveText('Stage 2 of 2: log');
  await page.getByRole('button', { name: 'MCP Pipeline', exact: true }).click();
  await expect(explorer.locator('.stage-position')).toHaveText('Stage 1 of 2: mapping');
  await page.keyboard.press('ArrowRight');
  await expect(explorer.locator('.stage-position')).toHaveText('Stage 2 of 2: log');
  await page.setViewportSize({ width: 320, height: 800 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(320);
  for (const theme of ['light', 'dark']) {
    await page.evaluate(value => document.documentElement.setAttribute('data-theme', value), theme);
    const results = await new AxeBuilder({ page }).include('.step-explorer').analyze();
    expect(results.violations.filter(item => ['serious', 'critical'].includes(item.impact))).toEqual([]);
  }
});

test('an outdated execution record is never presented as current stage data', async ({ page }) => {
  await page.route('**/pipeline-*.explorer.json', async route => {
    const response = await route.fetch();
    const trace = await response.json();
    trace.pipeline_sha256 = 'outdated';
    await route.fulfill({ json: trace });
  });
  await page.goto('/skill/slug-generate/');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const explorer = page.locator('.step-explorer:visible');
  await expect(explorer).toContainText('No current execution record');
  await expect(explorer.locator('.stage-output')).toHaveCount(0);
});

test('every published page has current recorded stage input and output', async ({ page }) => {
  test.setTimeout(600_000);
  const catalog = await (await page.request.get('/catalog.json')).json();
  const missing = [];
  for (const name of Object.keys(catalog.skills)) {
    await page.goto(`/skill/${name}/`);
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
    const variants = page.locator('.pipeline-sub-tab');
    for (let index = 0; index < await variants.count(); index += 1) {
      await variants.nth(index).click();
      const explorer = page.locator('.step-explorer:visible');
      if (await explorer.locator('.stage-input').count() === 0 ||
          await explorer.locator('.stage-output').count() === 0) {
        missing.push(`${name}: ${await variants.nth(index).textContent()}`);
        continue;
      }
      const filename = (await explorer.getAttribute('data-pipeline-file')).replace('.yaml', '.explorer.json');
      // This JSON is the published execution-record contract, not source code.
      const record = await (await page.request.get(`/${name}/${filename}`)).json();
      for (let stage = 0; stage < record.stages.length; stage += 1) {
        await expect(explorer.locator('.stage-input')).toHaveText(JSON.stringify(record.stages[stage].input, null, 2));
        await expect(explorer.locator('.stage-output')).toHaveText(JSON.stringify(record.stages[stage].output, null, 2));
        if (stage + 1 < record.stages.length) {
          const scroll = await page.locator('#skill-modal').evaluate(el => el.scrollTop);
          await page.keyboard.press('ArrowRight');
          await expect(explorer.locator('.stage-position')).toHaveText(`Stage ${stage + 2} of ${record.stages.length}: ${record.stages[stage + 1].name}`);
          expect(await page.locator('#skill-modal').evaluate(el => el.scrollTop)).toBe(scroll);
        }
      }
    }
  }
  expect(missing, 'Each published variant requires a byte-bound Edge stage record').toEqual([]);
});

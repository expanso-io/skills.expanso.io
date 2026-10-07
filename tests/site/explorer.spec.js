const { test, expect } = require('@playwright/test');

const { execFileSync } = require('node:child_process');

const { createHash } = require('node:crypto');

test('empty recorded stage values report clipboard success and failure', async ({ context, page }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('/skill/date-now/');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const input = page.locator('.stage-explorer:visible .stage-input');
  await expect(input.locator('code')).toHaveText('');
  const copy = input.locator('.copy-btn');
  await copy.click();
  await expect(copy).toHaveText('Copied');
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe('');
  await page.evaluate(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error('forced failure')) }
    });
    document.execCommand = () => false;
  });
  await copy.click();
  await expect(copy).toHaveText('Copy failed');
});

test('stage values preserve text and structured JSON', async ({ page }) => {
  await page.goto('/skill/slug-generate/');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const explorer = page.locator('.stage-explorer:visible');

  await explorer.getByRole('button', { name: /^Stage 2:/ }).click();
  await expect(explorer.locator('.stage-input')).toContainText('Hello World');
  const output = await explorer.locator('.stage-output code').textContent();

  expect(JSON.parse(output).slug).toBe('hello-world-this-is-a-test');
});

test('CSV conversion exposes every published variant and its recorded stages', async ({ page }) => {
  const ledger = await (await page.request.get('/example-conformance.json')).json();
  const published = ledger.examples.filter(row => row.status !== 'pulled' && row.pipeline.split('/').at(-2) === 'csv-to-json');
  await page.goto('/skill/csv-to-json/');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const tabs = page.locator('.pipeline-sub-tabs > button');
  await expect(tabs).toHaveCount(published.length);
  const observed = [];

  for (let index = 0; index < await tabs.count(); index += 1) {
    await tabs.nth(index).click();

    const content = page.locator('.copy-pipeline-banner:visible').locator('..');
    observed.push(await content.locator('.code-block:not(.stage-config):not(.stage-input):not(.stage-output) code').first().textContent());

    const explorer = content.locator('.stage-explorer');
    await expect(explorer).toBeVisible();

    for (const value of ['.stage-input', '.stage-output']) {
      await expect(explorer.locator(value)).not.toHaveText('Not recorded');
    }
  }

  for (const row of published) {
    const source = await (await page.request.get(`/csv-to-json/${row.pipeline.split('/').at(-1)}`)).text();

    expect(observed).toContain(source);
  }
});

test('intact published MCP listener responds at configured PORT', () => {
  test.setTimeout(90_000);
  const output = execFileSync('uv', ['run', '-s', 'scripts/test-mcp-listener.py'], { encoding: 'utf8', timeout: 80_000 });
  expect(output).toContain('Intact published MCP adapter: hello-world');
});

test('pipeline stages expose recorded input/output and preserve scroll', async ({ page }) => {
  await page.goto('/skill/slug-generate');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const explorer = page.locator('.stage-explorer:visible');
  await expect(explorer).toBeVisible();
  const stages = explorer.getByRole('button', { name: /^Stage / });
  expect(await stages.count()).toBeGreaterThan(1);
  await stages.first().click();
  await expect(explorer.locator('.stage-input')).toContainText('Hello');
  await page.locator('.modal').evaluate(el => { el.scrollTop = 180; });
  const before = await page.locator('.modal').evaluate(el => el.scrollTop);
  await page.keyboard.press('ArrowRight');
  await expect(stages.nth(1)).toHaveAttribute('aria-pressed', 'true');
  await expect(explorer.locator('.stage-output')).toContainText('hello-world');
  expect(await page.locator('.modal').evaluate(el => el.scrollTop)).toBe(before);
  await page.keyboard.press('ArrowLeft');
  await expect(stages.first()).toHaveAttribute('aria-pressed', 'true');
  expect(await page.locator('.modal').evaluate(el => el.scrollTop)).toBe(before);
});

// The staged catalog is the published skill inventory; give each sibling its
// own budget so the total catalog size cannot time out an otherwise passing sweep.
for (const name of Object.keys(require('../../docs/catalog.json').skills)) {
  test(`every published sibling exposes its actual pipeline stages: ${name}`, async ({ page }) => {
    test.setTimeout(120_000);
    const ledger = await (await page.request.get('/example-conformance.json')).json();
    let variants = 0;

    await page.goto(`/skill/${name}/`);
    await page.getByRole('button', { name: 'Pipeline', exact: true }).click();

    // Variant controls have their own container, separate from stage controls.
    const variantTabs = page.locator('.pipeline-sub-tabs > button');
    const published = ledger.examples.filter(row => row.status !== 'pulled' && row.pipeline.split('/').at(-2) === name);

    await expect(variantTabs, `${name} published variant coverage`).toHaveCount(published.length);

    for (let index = 0; index < await variantTabs.count(); index += 1) {
      await variantTabs.nth(index).click();

      const explorer = page.locator('.stage-explorer:visible');
      await expect(explorer).toBeVisible();

      const stages = explorer.getByRole('button', { name: /^Stage / });
      expect(await stages.count(), `${name} variant ${index}`).toBeGreaterThan(0);
      await stages.last().click();

      await expect(stages.last()).toHaveAttribute('aria-pressed', 'true');
      await expect(explorer.locator('.stage-config')).not.toHaveText('');
      await expect(explorer.locator('.stage-input')).toBeVisible();
      await expect(explorer.locator('.stage-output')).toBeVisible();

      for (let stage = 0; stage < await stages.count(); stage += 1) {
        await stages.nth(stage).click();
        await expect(explorer.locator('.stage-input')).not.toHaveText('Not recorded');
        await expect(explorer.locator('.stage-output')).not.toHaveText('Not recorded');
      }

      const before = await page.locator('.modal').evaluate(el => el.scrollTop);
      await page.keyboard.press('ArrowLeft');
      expect(await page.locator('.modal').evaluate(el => el.scrollTop)).toBe(before);
      variants += 1;
    }
    console.log(`Explorer sweep: ${name}, ${variants} variants`);
  });
}

test('published explorer data records current input and output for every stage', async ({ request }) => {
  const catalog = await (await request.get('/catalog.json')).json();

  const ledger = await (await request.get('/example-conformance.json')).json();
  const missing = [];
  let variants = 0;

  for (const name of Object.keys(catalog.skills)) {
    const response = await request.get(`/${name}/explorer.json`);
    expect(response.ok(), name).toBeTruthy();

    const data = await response.json();

    const published = ledger.examples.filter(row => row.status !== 'pulled' && row.pipeline.split('/').at(-2) === name)
      .map(row => row.pipeline.split('/').at(-1)).sort();

    expect(Object.keys(data).sort(), `${name} variant coverage`).toEqual(published);

    for (const [variant, recording] of Object.entries(data)) {
      variants += 1;
      const pipeline = await request.get(`/${name}/${variant}`);
      expect(pipeline.ok(), `${name}/${variant}`).toBeTruthy();
      expect(recording.sha256).toBe(createHash('sha256').update(await pipeline.body()).digest('hex'));
      expect(recording.stages.length, `${name}/${variant}`).toBeGreaterThan(1);

      for (const [index, stage] of recording.stages.entries()) {
        if (!Object.hasOwn(stage, 'input') || !Object.hasOwn(stage, 'output')) {
          missing.push(`${name}/${variant} stage ${index}`);
        }
      }
    }
  }

  console.log(`Explorer value sweep: ${Object.keys(catalog.skills).length} skills, ${variants} variants`);

  expect(missing.length, `Missing values: ${missing.slice(0, 12).join(', ')}`).toBe(0);
});

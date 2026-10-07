const { test, expect } = require('@playwright/test');

const AxeBuilder = require('@axe-core/playwright').default;

async function waitForCatalog(page) {
  await page.goto('/');
  await expect(page.locator('.skill-card').first()).toBeVisible();
}

async function expectNoHorizontalOverflow(page) {
  const offenders = await page.locator('body *').evaluateAll((elements) => {
    const viewportWidth = document.documentElement.clientWidth;

    return elements.flatMap((element) => {
      const style = window.getComputedStyle(element);
      const rect = element.getBoundingClientRect();

      const visible = style.display !== 'none' && style.visibility !== 'hidden' &&
        rect.width > 0 && rect.height > 0;

      if (!visible || (rect.left >= -0.5 && rect.right <= viewportWidth + 0.5)) {
        return [];
      }

      return [`${element.tagName.toLowerCase()}.${element.className}: ` +
        `${rect.left.toFixed(1)}..${rect.right.toFixed(1)} / ${viewportWidth}`];
    });
  });

  expect(offenders).toEqual([]);
}

async function expectNoSeriousAxeViolations(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    // Allow newly applied styles to create their transitions before observing them.
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  });
  await page.waitForFunction(() => document.getAnimations().every(animation =>
    animation.playState !== 'running' && !animation.pending));
  const results = await new AxeBuilder({ page }).analyze();

  const violations = results.violations.filter((violation) =>
    ['serious', 'critical'].includes(violation.impact));

  expect(violations).toEqual([]);
}

async function expectVisibleCopiesSucceed(page) {
  const controls = page.locator(
    '#modal-content .copy-pipeline-btn:visible, ' +
    '#modal-content .code-copy-btn:visible'
  );

  const count = await controls.count();

  for (let index = 0; index < count; index += 1) {
    const control = controls.nth(index);
    await control.click();
    await expect(control).toHaveText(/Copied/);
  }
}

test('copy controls report success and failure on the clicked control', async ({
  context,
  page
}) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await waitForCatalog(page);

  const installCopy = page.locator('.install-box .copy-btn');
  await installCopy.click();
  await expect(installCopy).toHaveText('Copied');

  await page.evaluate(() => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: () => Promise.reject(new Error('forced failure')) }
    });
    document.execCommand = () => false;
  });
  await expect(installCopy).toHaveText('Copy', { timeout: 4_000 });
  await installCopy.click();
  await expect(installCopy).toHaveText('Copy failed');

  await page.locator('.skill-card').first().click();
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  const variantTabs = page.locator('.pipeline-sub-tab');
  const variantCount = await variantTabs.count();

  for (let variant = 0; variant < variantCount; variant += 1) {
    await variantTabs.nth(variant).click();

    const controls = page.locator(
      '#modal-content .copy-pipeline-btn:visible, ' +
      '#modal-content .code-copy-btn:visible'
    );

    const controlCount = await controls.count();
    expect(controlCount).toBeGreaterThan(0);

    for (let index = 0; index < controlCount; index += 1) {
      const control = controls.nth(index);
      await control.click();
      await expect(control).toHaveText('Copy failed');
    }
  }
});

test('light and dark surfaces have no serious accessibility violations', async ({
  page
}) => {
  test.setTimeout(60_000);
  await waitForCatalog(page);
  // Exercise rendering readiness with transitions longer than a fixed delay.
  await page.addStyleTag({ content: `
    * { transition-duration: 2s !important; }
    .tab-content { animation-duration: 2s !important; }
  ` });
  await expectNoSeriousAxeViolations(page);
  await page.locator('.skill-card').first().click();
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  await expectNoSeriousAxeViolations(page);
  await page.evaluate(() => document.querySelector('#theme-toggle').click());
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expectNoSeriousAxeViolations(page);
});

test('page and modal wrap at 320px without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await waitForCatalog(page);
  await expectNoHorizontalOverflow(page);
  await page.locator('.skill-card').first().click();
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  await expectNoHorizontalOverflow(page);
});

test('escaped YAML remains within the phone viewport', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/skill/secrets-scan');
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  await expect(page.locator('#modal-content .code-block:visible code').first())
    .toBeVisible();
  await expectNoHorizontalOverflow(page);
});

const publishedNames = [...new Set(require('../../docs/example-conformance.json').examples
  .filter(row => row.status !== 'pulled')
  .map(row => row.pipeline.split('/').at(-2)))].sort();

for (const name of publishedNames) {
  test(`published page preserves features and usability: ${name}`, async ({
    context,
    page
  }) => {
    test.setTimeout(180_000);
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto(`/skill/${name}`);
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'light');
      localStorage.setItem('theme', 'light');
    });
    await expect(page.locator('#modal-overlay')).toHaveClass(/active/);
    await expect(page.getByRole('button', { name: 'Spec', exact: true }))
      .toBeVisible();
    await expect(page.getByRole('button', { name: 'Pipeline', exact: true }))
      .toBeVisible();

    await expect(page.locator(".modal-description")).not.toHaveText("");
    await expectVisibleCopiesSucceed(page);
    await expectNoSeriousAxeViolations(page);
    await page.evaluate(() => document.querySelector('#theme-toggle').click());
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
    await expectNoSeriousAxeViolations(page);

    await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
    const variants = page.locator('.pipeline-sub-tab');
    const variantCount = await variants.count();
    expect(variantCount, `${name} must retain a published pipeline variant`)
      .toBeGreaterThan(0);

    for (let variant = 0; variant < variantCount; variant += 1) {
      await variants.nth(variant).click();
      await expect(page.getByRole("heading", { name: "Deploy", exact: true })).toBeVisible();
      await expectVisibleCopiesSucceed(page);
    }

    await page.setViewportSize({ width: 320, height: 800 });
    await expectNoHorizontalOverflow(page);
  });
}

test('retains deep links, spec and pipeline tabs, theme, and job proof', async ({
  page
}) => {
  await waitForCatalog(page);
  await page.locator('.skill-card').first().click();
  await expect(page).toHaveURL(/\/skill\/[^/]+\/$/);
  await expect(page.getByRole('button', { name: 'Spec', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Pipeline', exact: true })).toBeVisible();
  const deepLink = page.url();
  await page.reload();
  await expect(page).toHaveURL(deepLink);
  await expect(page.locator('#modal-overlay')).toHaveClass(/active/);

  await page.locator('.modal-close').click();
  await page.getByRole('button', { name: 'Switch to dark theme' }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

  await page.getByRole('tab', { name: 'Jobs', exact: true }).click();
  await page.locator('.skill-card').first().click();
  await page.getByRole('button', { name: 'Pipeline', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Proof', exact: true })).toBeVisible();
  await expect(page.locator('#modal-content .code-block:visible:not(.stage-config):not(.stage-input):not(.stage-output) code').first())
    .toContainText('type: pipeline');
});

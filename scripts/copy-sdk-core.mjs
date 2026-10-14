// Copies the core of the pinned posthog-js (node_modules/posthog-js/dist/array.js, the
// version package.json pins) into docs/js/array-<version>.js, the file js/analytics.js loads.
// Part of `npm run build`; the copy is git-ignored, like the consent runtime.
//
// The name carries the version, so a posthog-js update that forgets the name in analytics.js
// fails scripts/check-site-tags.py. It has no "posthog" in it, because filter lists block
// such paths. Older copies are removed, so a local build matches a fresh CI build.
import { copyFileSync, readdirSync, readFileSync, rmSync } from 'node:fs';

const sdk = new URL('../node_modules/posthog-js/', import.meta.url);
const out = new URL('../docs/js/', import.meta.url);
const { version } = JSON.parse(readFileSync(new URL('package.json', sdk), 'utf8'));
const pinned = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
  .devDependencies['posthog-js'];
// After a pull that changes the pin, node_modules still has the old SDK until `npm ci`.
if (version !== pinned) {
  console.error(`node_modules has posthog-js ${version}, package.json pins ${pinned}: run npm ci`);
  process.exit(1);
}
const name = `array-${version}.js`;

// Only versioned copies of the core (array-1.435.6.js), never another site file.
for (const file of readdirSync(out)) {
  if (/^array-\d+\.\d+\.\d+[\w.-]*\.js$/.test(file) && file !== name) rmSync(new URL(file, out));
}
copyFileSync(new URL('dist/array.js', sdk), new URL(name, out));
console.log(`docs/js/${name} (posthog-js ${version})`);

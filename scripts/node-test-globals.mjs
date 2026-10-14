// The shared consent test is written in Jest style (describe/it/beforeEach as globals) so
// it runs unchanged in expanso-cloud. Under `node --test` those come from node:test; this
// preload puts them on globalThis. Used via `node --import ./scripts/node-test-globals.mjs`.
import { beforeEach, describe, it } from 'node:test';

globalThis.describe = describe;
globalThis.it = it;
globalThis.beforeEach = beforeEach;

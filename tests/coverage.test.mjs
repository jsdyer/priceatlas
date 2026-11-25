import test from 'node:test';
import assert from 'node:assert/strict';
import { observationRange, sharedIndexes } from '../web/coverage.mjs';

const months = ['2025-07', '2025-08', '2025-09', '2025-10'];
const product = { regions: { CA: [2, 2.2, 2.3, 2.4], ON: [2.1, null, 2.5, 2.6], YT: [null, null, 4, 4.2], NU: [null, null, null, null] } };

test('northern coverage starts at an actual price, not at the national start date', () => {
  assert.deepEqual(observationRange(product, 'YT', months), { first: '2025-09', last: '2025-10', count: 2 });
  assert.deepEqual(observationRange(product, 'NU', months), { first: null, last: null, count: 0 });
  assert.deepEqual(observationRange(product, 'unknown', months), { first: null, last: null, count: 0 });
});

test('indexes and changes use only shared months of selected areas', () => {
  assert.deepEqual(sharedIndexes(product, ['CA', 'ON'], [0, 1, 2, 3]), [0, 2, 3]);
  assert.deepEqual(sharedIndexes(product, ['CA', 'ON', 'YT'], [0, 1, 2, 3]), [2, 3]);
  assert.deepEqual(sharedIndexes(product, ['CA', 'NU'], [0, 1, 2, 3]), []);
  assert.deepEqual(sharedIndexes(product, [], [0, 1, 2, 3]), []);
});

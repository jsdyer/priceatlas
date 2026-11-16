import test from 'node:test';
import assert from 'node:assert/strict';
import { basketTotal } from '../web/basket.mjs';

test('sums quantities using the published package prices', () => {
  const products = [
    { id: 'eggs', name: 'Eggs, 1 dozen', regions: { CA: [4.5] } },
    { id: 'milk', name: 'Milk, 2 litres', regions: { CA: [3.4] } },
  ];
  assert.equal(basketTotal(products, new Map([['eggs', 2], ['milk', 1]]), 'CA', 0).total, 12.4);
});

test('withholds the entire total and identifies missing source observations', () => {
  const products = [
    { id: 'eggs', name: 'Eggs', regions: { CA: [4.5] } },
    { id: 'milk', name: 'Milk', regions: { CA: [null] } },
  ];
  assert.deepEqual(basketTotal(products, new Map([['eggs', 1], ['milk', 1]]), 'CA', 0), { total: null, missing: ['Milk'] });
  assert.equal(basketTotal([], new Map(), 'CA', 0).total, null);
});


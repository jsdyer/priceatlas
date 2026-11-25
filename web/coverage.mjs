/** Published coverage of one product; never infer a price across missing months. */
export function observationRange(product, code, months) {
  const indexes = (product?.regions?.[code] ?? []).flatMap((value, index) => Number.isFinite(value) ? [index] : []);
  return { first: months[indexes[0]] ?? null, last: months[indexes.at(-1)] ?? null, count: indexes.length };
}

export function sharedIndexes(product, areas, indexes) {
  return areas.length ? indexes.filter(index => areas.every(code => Number.isFinite(product?.regions?.[code]?.[index]))) : [];
}

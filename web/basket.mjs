/** Sum the same published packages only when every observation exists. */
export function basketTotal(products, quantities, area, index) {
  const missing = [];
  let total = 0;
  for (const product of products) {
    const price = product.regions[area]?.[index];
    const quantity = quantities.get(product.id);
    if (!Number.isFinite(price)) {
      missing.push(product.name);
    } else {
      total += price * quantity;
    }
  }
  return { total: missing.length || !products.length ? null : total, missing };
}

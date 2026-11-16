import { basketTotal } from './basket.mjs';
import { createChart, createTable, csvDownload, element, get, setOptions, subtractMonths } from './series.mjs';

const fields = Object.fromEntries(['search', 'product', 'unit', 'from', 'through'].map(id => [id, get(id)]));
const areaBoxes = [...document.querySelectorAll('[name="area"]')];
const days = [...document.querySelectorAll('[data-months]')];
const chart = createChart();
const table = createTable();
const currency = new Intl.NumberFormat('en-CA', { style: 'currency', currency: 'CAD' });
const fmt = value => currency.format(value);
const validMonth = value => /^\d{4}-(0[1-9]|1[0-2])$/.test(value ?? '');
const geographyCodes = areaBoxes.map(box => box.value);
const allowedUnits = ['package', 'standard', 'index'];
let data;
let exportData;
const basket = new Map();
let basketExport = [];

function showStatus(message, isError = false) {
  const status = get('status');
  status.textContent = message;
  status.hidden = !message;
  status.classList.toggle('error', isError);
}

function latestCommon(product, areas) {
  return data.months.findLastIndex((_, index) => areas.every(code => Number.isFinite(product.regions[code][index])));
}

function renderOverview(product) {
  const latest = latestCommon(product, geographyCodes);
  get('overview-product').textContent = product.name;
  geographyCodes.forEach(code => {
    const value = product.regions[code][latest];
    get('hero-' + code).textContent = Number.isFinite(value) ? fmt(value) : '—';
  });
  const lastDate = latest >= 0 ? 'Published month ' + data.months[latest] + ' · ' : '';
  get('snapshot').textContent = lastDate + 'Built ' + data.built.slice(0, 10) + ' UTC';
}

function normalizeSearch(text) {
  return text.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLocaleLowerCase('en-CA').trim();
}

function setupProducts(selected) {
  const terms = normalizeSearch(fields.search.value).split(/\s+/).filter(Boolean);
  const options = data.products.filter(product => terms.every(term => normalizeSearch(product.name).includes(term)))
    .map(product => [product.id, product.name]);
  setOptions(fields.product, options, selected);
  fields.product.disabled = !options.length;
}

function range(months) {
  const last = data.months.at(-1);
  const target = months ? subtractMonths(last, months - 1) : data.months[0];
  fields.from.value = target < data.months[0] ? data.months[0] : target;
  fields.through.value = last;
}

function updateRangeButtons() {
  days.forEach(button => {
    const months = Number(button.dataset.months);
    const last = data.months.at(-1);
    const first = months ? subtractMonths(last, months - 1) : data.months[0];
    button.setAttribute('aria-pressed', String(fields.through.value === last && fields.from.value === first));
  });
}

function render() {
  const product = data.products.find(row => row.id === fields.product.value);
  const areas = areaBoxes.filter(box => box.checked).map(box => box.value);
  const min = fields.from.value;
  const max = fields.through.value;
  const badRange = !validMonth(min) || !validMonth(max) || min > max;
  const indexes = data.months.map((_, n) => n).filter(n => data.months[n] >= min && data.months[n] <= max);
  const covered = product && indexes.some(index => areas.some(code => Number.isFinite(product.regions[code][index])));
  updateRangeButtons();
  renderBasket();
  if (product) renderOverview(product);
  fields.unit.querySelector('[value="standard"]').disabled = !product?.unit;
  if (fields.unit.value === 'standard' && !product?.unit) fields.unit.value = 'package';
  if (!product || !areas.length || badRange || !covered) {
    get('plot').hidden = true;
    get('export').disabled = true;
    showStatus(!product ? 'No products match that search.' : !areas.length ? 'Select at least one area.'
      : badRange ? 'Enter a valid start and end month in order.' : 'No observations for these areas and months.');
    return;
  }
  const unit = fields.unit.value;
  const shared = indexes.filter(index => areas.every(code => Number.isFinite(product.regions[code][index])));
  if (unit === 'index' && !shared.length) {
    get('plot').hidden = true;
    get('export').disabled = true;
    showStatus('No shared observation month to use as an index baseline. Choose another date range or area.');
    return;
  }
  get('plot').hidden = false;
  get('export').disabled = false;
  showStatus('');
  const dates = indexes.map(index => data.months[index]);
  const format = unit === 'index' ? value => value.toFixed(1) : fmt;
  const tracks = areas.map(code => {
    const source = product.regions[code];
    const raw = indexes.map(index => source[index]);
    const divisor = unit === 'index' ? source[shared[0]] / 100
      : unit === 'standard' ? product.unit.quantity : 1;
    return {
      label: data.groups[code], vector: product.vectors[code], raw,
      values: raw.map(price => price === null ? null : price / divisor),
      change: shared.length > 1 ? 100 * (source[shared.at(-1)] / source[shared[0]] - 1) : null,
    };
  });
  chart({ dates, tracks, format, breakGaps: true });
  get('chart-title').textContent = product.name;
  const unitLabel = unit === 'index' ? 'Index · ' + data.months[shared[0]] + ' = 100'
    : unit === 'standard' ? 'CAD per ' + product.unit.unit : 'CAD per published package or price unit';
  const comparison = shared.length > 1 ? ' · Change from ' + data.months[shared[0]] + ' through ' + data.months[shared.at(-1)] : '';
  get('chart-description').textContent = unitLabel + comparison;
  const changes = get('changes');
  changes.hidden = shared.length < 2;
  changes.replaceChildren(...tracks.map(track => {
    const panel = element('div');
    const change = track.change;
    panel.append(element('dt', track.label), element('dd', Number.isFinite(change)
      ? (change > 0 ? '+' : '') + change.toFixed(1) + '%' : '—'));
    return panel;
  }));
  table(['Month', ...tracks.map(track => track.label)], dates.map((date, n) => [
    date, ...tracks.map(track => Number.isFinite(track.values[n]) ? format(track.values[n]) : '—'),
  ]));
  exportData = {
    headings: ['month', 'product', 'area', 'StatCan vector', 'published price (CAD)', 'chart value', 'chart unit'],
    rows: dates.flatMap((date, n) => tracks.map(track => [
      date, product.name, track.label, track.vector, track.raw[n],
      Number.isFinite(track.values[n]) ? Number(track.values[n].toFixed(6)) : null,
      unitLabel,
    ])),
  };
  history.replaceState(null, '', '?' + new URLSearchParams({ product: product.id, areas: areas.join(','), unit, from: min, through: max }));
}


function renderBasket() {
  const section = get('basket');
  section.hidden = basket.size === 0;
  if (!basket.size) return;
  const products = data.products.filter(product => basket.has(product.id));
  get('basket-items').replaceChildren(...products.map(product => {
    const row = element('div');
    row.className = 'basket-item';
    const name = element('span', product.name);
    const label = element('label', 'Packages');
    const quantity = element('input');
    quantity.type = 'number';
    quantity.min = '1';
    quantity.max = '99';
    quantity.step = '1';
    quantity.value = String(basket.get(product.id));
    quantity.setAttribute('aria-label', 'Packages of ' + product.name);
    quantity.addEventListener('change', () => {
      const value = Number(quantity.value);
      basket.set(product.id, Number.isInteger(value) && value >= 1 && value <= 99 ? value : 1);
      renderBasket();
    });
    label.append(quantity);
    const remove = element('button', 'Remove');
    remove.type = 'button';
    remove.setAttribute('aria-label', 'Remove ' + product.name);
    remove.addEventListener('click', () => { basket.delete(product.id); renderBasket(); });
    row.append(name, label, remove);
    return row;
  }));
  const areas = areaBoxes.filter(box => box.checked).map(box => box.value);
  const dates = [fields.from.value, fields.through.value];
  const indexes = dates.map(date => data.months.indexOf(date));
  const valid = areas.length && indexes.every(index => index >= 0) && dates[0] <= dates[1];
  get('basket-export').disabled = !valid;
  if (!valid) {
    get('basket-status').textContent = 'Select an area and valid From and Through months within the data range.';
    get('basket-totals').replaceChildren();
    basketExport = [];
    return;
  }
  const missing = [];
  basketExport = [];
  const rows = areas.map(area => {
    const results = indexes.map((index, n) => {
      const result = basketTotal(products, basket, area, index);
      if (result.missing.length) missing.push(data.groups[area] + ' · ' + dates[n] + ': ' + result.missing.join(', '));
      for (const product of products) {
        basketExport.push([dates[n], data.groups[area], product.name, basket.get(product.id),
          product.regions[area]?.[index] ?? null, product.vectors[area]]);
      }
      return result.total;
    });
    const [first, last] = results;
    const change = Number.isFinite(first) && first > 0 && Number.isFinite(last) ? (last / first - 1) * 100 : null;
    const tr = element('tr');
    const th = element('th', data.groups[area]);
    th.scope = 'row';
    tr.append(th, ...[first, last].map(value => element('td', Number.isFinite(value) ? fmt(value) : '—')),
      element('td', Number.isFinite(change) ? (change > 0 ? '+' : '') + change.toFixed(1) + '%' : '—'));
    return tr;
  });
  get('basket-totals').replaceChildren(...rows);
  get('basket-status').textContent = missing.length ? 'Missing observations — ' + missing.join(' | ') : 'All selected items have prices for both months.';
}
get('basket-add').addEventListener('click', () => {
  const id = fields.product.value;
  if (!data?.products.some(product => product.id === id)) return;
  basket.set(id, basket.get(id) ?? 1);
  renderBasket();
  get('basket-heading').scrollIntoView({ behavior: 'smooth', block: 'start' });
});
get('basket-export').addEventListener('click', () => csvDownload('price-atlas-basket.csv',
  ['month', 'area', 'product', 'packages', 'published package price (CAD)', 'StatCan vector'], basketExport));

fields.search.addEventListener('input', () => { setupProducts(fields.product.value); render(); });
[fields.product, fields.unit, fields.from, fields.through, ...areaBoxes].forEach(field => field.addEventListener('change', render));
days.forEach(button => button.addEventListener('click', () => { range(Number(button.dataset.months)); render(); }));
get('export').addEventListener('click', () => csvDownload('canadian-price-atlas.csv', exportData.headings, exportData.rows));

async function load() {
  get('retry').hidden = true;
  showStatus('Loading monthly averages…');
  try {
    const response = await fetch('./snapshot.json');
    if (!response.ok) throw new Error('Snapshot HTTP ' + response.status);
    data = await response.json();
    if (!data.months?.length || !data.products?.length || !data.groups) throw new Error('Invalid snapshot');
    get('reference-month').textContent = data.months[0] + ' to ' + data.months.at(-1);
    const query = new URLSearchParams(location.search);
    setupProducts(query.get('product') ?? data.products.find(row => row.name === 'Eggs, 1 dozen')?.id);
    const unit = query.get('unit');
    if (allowedUnits.includes(unit)) fields.unit.value = unit;
    const areas = query.get('areas')?.split(',').filter(code => geographyCodes.includes(code));
    if (areas?.length) areaBoxes.forEach(box => { box.checked = areas.includes(box.value); });
    for (const key of ['from', 'through']) {
      fields[key].min = data.months[0];
      fields[key].max = data.months.at(-1);
    }
    range(36);
    for (const key of ['from', 'through']) {
      const month = query.get(key);
      if (validMonth(month) && month >= fields[key].min && month <= fields[key].max) fields[key].value = month;
    }
    get('controls').hidden = false;
    render();
  } catch (error) {
    get('snapshot').textContent = 'Data unavailable';
    showStatus('Could not open the data snapshot. Retry, or use the official source links below.', true);
    get('retry').hidden = false;
  }
}
get('retry').addEventListener('click', load);
load();

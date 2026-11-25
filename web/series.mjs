const DAY = 86400000;
const PALETTE = ['#306444', '#a04926', '#41607a', '#80599c', '#946b06', '#287d88', '#9a426a', '#5e6c23', '#3f589a', '#9a4e3e', '#576d62', '#765035', '#3d7084'];
const DASHES = [[], [8, 4], [2, 4]];
const shortDate = new Intl.DateTimeFormat('en-CA', { month: 'short', year: 'numeric', timeZone: 'UTC' });

export const get = id => document.getElementById(id);

export function element(tag, content) {
  const node = document.createElement(tag);
  if (content !== undefined) node.textContent = content;
  return node;
}

export function setOptions(select, rows, selected) {
  select.replaceChildren(...rows.map(([value, label]) => new Option(label, value)));
  if (rows.some(row => row[0] === selected)) select.value = selected;
}

export function csvDownload(name, headings, rows) {
  const cell = value => typeof value === 'number' ? String(value) : '"' + String(value ?? '').replaceAll('"', '""') + '"';
  const content = [headings, ...rows].map(row => row.map(cell).join(',')).join('\r\n') + '\r\n';
  const url = URL.createObjectURL(new Blob([content], { type: 'text/csv;charset=utf-8' }));
  const link = element('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export function subtractMonths(value, count) {
  const base = new Date(value.length === 7 ? value + '-01' : value);
  const target = new Date(Date.UTC(base.getUTCFullYear(), base.getUTCMonth() - count, 1));
  const daysInMonth = new Date(Date.UTC(target.getUTCFullYear(), target.getUTCMonth() + 1, 0)).getUTCDate();
  target.setUTCDate(Math.min(base.getUTCDate(), daysInMonth));
  return target.toISOString().slice(0, value.length);
}

export function createTable() {
  const head = get('table-head');
  const body = get('table-body');
  const previous = get('newer');
  const next = get('older');
  const label = get('page');
  const pageSize = 20;
  let currentPage = 0;
  let latestFirst = [];
  function render() {
    const pages = Math.max(1, Math.ceil(latestFirst.length / pageSize));
    body.replaceChildren(...latestFirst.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map(row => {
      const tr = element('tr');
      row.forEach((value, index) => {
        const cell = element(index ? 'td' : 'th', value);
        if (!index) cell.scope = 'row';
        tr.append(cell);
      });
      return tr;
    }));
    label.textContent = 'Page ' + (currentPage + 1) + ' of ' + pages;
    previous.disabled = currentPage === 0;
    next.disabled = currentPage + 1 >= pages;
  }
  previous.addEventListener('click', () => { currentPage--; render(); });
  next.addEventListener('click', () => { currentPage++; render(); });
  return (headers, rows) => {
    head.replaceChildren(...headers.map(value => {
      const th = element('th', value);
      th.scope = 'col';
      return th;
    }));
    latestFirst = [...rows].reverse();
    currentPage = 0;
    render();
  };
}

export function createChart() {
  const canvas = get('chart');
  const selected = get('selection');
  const slider = get('inspect');
  const legend = get('legend');
  let model;
  let index = 0;
  let layout;

  function draw() {
    if (!model || !model.dates.length) return;
    const { dates, tracks, format } = model;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * ratio);
    canvas.height = Math.round(h * ratio);
    const ctx = canvas.getContext('2d');
    ctx.scale(ratio, ratio);
    const left = w < 450 ? 57 : 82;
    const right = w - 9;
    const top = 18;
    const bottom = h - 32;
    const timestamps = dates.map(date => Date.parse(date.length === 7 ? date + '-01' : date));
    const start = timestamps[0];
    const span = timestamps.at(-1) - start || DAY;
    const position = n => dates.length === 1 ? (left + right) / 2 : left + (timestamps[n] - start) / span * (right - left);
    layout = { left, right, position };
    let low = Infinity;
    let high = -Infinity;
    for (const track of tracks) {
      for (const v of track.values) {
        if (!Number.isFinite(v)) continue;
        low = Math.min(v, low);
        high = Math.max(v, high);
      }
    }
    if (!Number.isFinite(low)) return;
    const spread = (high - low || Math.abs(high) * .12 || 1) * .12;
    low -= spread;
    high += spread;
    const y = value => bottom - (value - low) / (high - low) * (bottom - top);
    ctx.font = (w < 450 ? '10' : '12') + 'px monospace';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'right';
    ctx.fillStyle = '#525f50';
    ctx.strokeStyle = '#dce0d0';
    for (let i = 0; i < 5; i++) {
      const value = low + (high - low) * i / 4;
      const yy = y(value);
      ctx.beginPath();
      ctx.moveTo(left, yy);
      ctx.lineTo(right, yy);
      ctx.stroke();
      ctx.fillText(format(value, true), left - 5, yy);
    }
    ctx.textBaseline = 'alphabetic';
    const tickCount = Math.min(w < 450 ? 3 : 5, dates.length);
    for (let i = 0; i < tickCount; i++) {
      const ix = tickCount === 1 ? 0 : Math.round(i / (tickCount - 1) * (dates.length - 1));
      ctx.textAlign = i === 0 ? 'left' : i === tickCount - 1 ? 'right' : 'center';
      ctx.fillText(shortDate.format(timestamps[ix]), position(ix), h - 10);
    }
    tracks.forEach((track, i) => {
      ctx.strokeStyle = PALETTE[i % PALETTE.length];
      ctx.fillStyle = PALETTE[i % PALETTE.length];
      ctx.lineWidth = 2;
      ctx.setLineDash(DASHES[i % DASHES.length]);
      ctx.beginPath();
      let previous = null;
      track.values.forEach((value, n) => {
        if (!Number.isFinite(value)) {
          if (model.breakGaps) previous = null;
          return;
        }
        if (previous === null) ctx.moveTo(position(n), y(value));
        else {
          if (track.step) ctx.lineTo(position(n), y(previous));
          ctx.lineTo(position(n), y(value));
        }
        previous = value;
      });
      ctx.stroke();
      if (track.values.filter(Number.isFinite).length <= 40) {
        for (let n = 0; n < track.values.length; n++) {
          const value = track.values[n];
          if (!Number.isFinite(value)) continue;
          ctx.beginPath();
          ctx.arc(position(n), y(value), 2.6, 0, 2 * Math.PI);
          ctx.fill();
        }
      }
    });
    const marker = position(index);
    ctx.strokeStyle = '#7c886f';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(marker, top);
    ctx.lineTo(marker, bottom);
    ctx.stroke();
    tracks.forEach((track, i) => {
      const value = track.values[index];
      if (!Number.isFinite(value)) return;
      ctx.fillStyle = PALETTE[i % PALETTE.length];
      ctx.beginPath();
      ctx.arc(marker, y(value), 4.5, 0, 2 * Math.PI);
      ctx.fill();
    });
  }

  function select(n) {
    if (!model) return;
    index = n;
    slider.value = String(n);
    slider.setAttribute('aria-valuetext', model.dates[n]);
    selected.textContent = model.dates[n] + ' · ' + model.tracks.map(track => {
      const value = track.values[n];
      return track.label + ' ' + (Number.isFinite(value) ? model.format(value) : '—');
    }).join(' · ');
    draw();
  }
  slider.addEventListener('input', () => select(Number(slider.value)));
  canvas.addEventListener('click', event => {
    if (!model || !layout) return;
    const x = event.clientX - canvas.getBoundingClientRect().left;
    if (x < layout.left || x > layout.right) return;
    let min = Infinity;
    let nearest = 0;
    model.dates.forEach((_, n) => {
      const distance = Math.abs(layout.position(n) - x);
      if (distance < min) { nearest = n; min = distance; }
    });
    select(nearest);
  });
  new ResizeObserver(draw).observe(canvas);
  return data => {
    model = data;
    legend.replaceChildren(...model.tracks.map((track, i) => {
      const row = element('li', track.label);
      row.className = 'series-' + i;
      return row;
    }));
    slider.max = String(model.dates.length - 1);
    select(model.dates.length - 1);
  };
}

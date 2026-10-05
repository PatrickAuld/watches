import { renderWatchFace } from 'https://cdn.jsdelivr.net/npm/wff-web@0.1.1/dist/index.js';
import { escapeHtml, faceUrl, loadCatalog, loadFace, prepare } from './render.js';

const root = document.body.dataset.root;
const slug = document.body.dataset.face;

const canvas = document.getElementById('watch-canvas');
const facePicker = document.getElementById('face-picker');
const timeInput = document.getElementById('time-input');
const timeModeSelect = document.getElementById('time-mode');
const ambientToggle = document.getElementById('ambient-toggle');
const styleCard = document.getElementById('style-card');
const stylePicker = document.getElementById('style-picker');
const paletteCard = document.getElementById('palette-card');
const palettePicker = document.getElementById('palette-picker');
const animateToggle = document.getElementById('animate-toggle');
const quickBtns = document.querySelectorAll('[data-set-time]');
const metaPanel = document.getElementById('meta-panel');
const placeholder = document.getElementById('placeholder');

let face = null;
let renderResult = null;
let renderVersion = 0;

function optionsHtml(options) {
  return options.map(o => `<option value="${escapeHtml(o.id)}">${escapeHtml(o.label)}</option>`).join('');
}

async function init() {
  const catalog = await loadCatalog(root);
  facePicker.innerHTML = catalog.map(f =>
    `<option value="${escapeHtml(f.slug)}">${escapeHtml(f.name)} (${escapeHtml(f.status)})</option>`
  ).join('');
  facePicker.value = slug;
  facePicker.addEventListener('change', () => { location.href = faceUrl(root, facePicker.value); });

  loadMetadata();

  const entry = catalog.find(f => f.slug === slug);
  if (!entry || !entry.xml) {
    showPlaceholder('In design — no watchface.xml yet');
    for (const id of ['time-card', 'display-card']) document.getElementById(id).hidden = true;
    return;
  }

  timeInput.value = '2026-03-13T10:10';
  timeInput.addEventListener('input', () => { timeModeSelect.value = 'fixed'; render(); });
  for (const el of [timeModeSelect, ambientToggle, stylePicker, palettePicker, animateToggle]) {
    el.addEventListener('change', render);
  }
  quickBtns.forEach(btn => btn.addEventListener('click', () => {
    timeInput.value = `2026-03-13T${btn.dataset.setTime}`;
    timeModeSelect.value = 'fixed';
    render();
  }));

  try {
    face = await loadFace(root, entry);
  } catch (error) {
    showPlaceholder(error.message);
    return;
  }

  styleCard.hidden = !face.style;
  if (face.style) {
    stylePicker.closest('label').querySelector('span').textContent = face.style.label;
    stylePicker.innerHTML = optionsHtml(face.style.options);
    stylePicker.value = face.style.defaultValue;
  }
  paletteCard.hidden = !face.palette;
  if (face.palette) {
    palettePicker.innerHTML = optionsHtml(face.palette.options);
    palettePicker.value = face.palette.defaultValue;
  }

  showCanvas();
  await render();
}

function showPlaceholder(message) {
  canvas.style.display = 'none';
  placeholder.style.display = 'block';
  placeholder.textContent = message;
}

function showCanvas() {
  canvas.style.display = 'block';
  placeholder.style.display = 'none';
}

function getTime() {
  if (timeModeSelect.value === 'live') return new Date();
  return new Date(timeInput.value || '2026-03-13T10:10');
}

async function render() {
  if (!face) return;
  const version = ++renderVersion;
  if (renderResult && renderResult.stop) {
    renderResult.stop();
    renderResult = null;
  }
  const animate = animateToggle.checked;
  try {
    const input = await prepare(face, {
      style: face.style ? stylePicker.value : undefined,
      palette: face.palette ? palettePicker.value : undefined,
    });
    if (version !== renderVersion) return;
    renderResult = await renderWatchFace(canvas, {
      ...input,
      width: 450,
      height: 450,
      time: animate ? undefined : getTime(),
      ambient: ambientToggle.checked,
      animate,
    });
  } catch (error) {
    showPlaceholder(`Render error: ${error.message}`);
  }
}

async function loadMetadata() {
  try {
    const response = await fetch(`${root}faces/${slug}/face.yaml`);
    if (!response.ok) throw new Error('not found');
    metaPanel.innerHTML = `<pre class="yaml">${escapeHtml(await response.text())}</pre>`;
  } catch {
    metaPanel.innerHTML = '<p class="muted">No metadata found</p>';
  }
}

// Live mode ticker
setInterval(() => {
  if (face && timeModeSelect.value === 'live' && !animateToggle.checked) render();
}, 1000);

init();

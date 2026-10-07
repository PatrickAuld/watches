import { renderWatchFaceFrame } from './vendor/wff-web.js';
import { escapeHtml, loadCatalog, loadFace, prepare } from './render.js';

const root = document.body.dataset.root;
const slug = document.body.dataset.face;

const $ = id => document.getElementById(id);
const canvas = $('watch-canvas');
const placeholder = $('placeholder');
const controls = $('controls');
const timeChips = $('time-chips');
const timeInput = $('time-input');
const ambientToggle = $('ambient-toggle');
const readout = $('readout');
const clock = $('clock');
const clockMode = $('clock-mode');

let face = null;
let style;
let palette;
// Milliseconds between the face's clock and real time; 0 means live.
let offset = 0;
let input = null;
let looping = false;
let paused = false;
let prepareVersion = 0;
const startedAt = performance.now();

async function init() {
  loadMetadata();

  const catalog = await loadCatalog(root);
  const entry = catalog.find(f => f.slug === slug);
  if (!entry || !entry.xml) return showPlaceholder('In design — no watchface.xml yet');

  try {
    face = await loadFace(root, entry);
  } catch (error) {
    return showPlaceholder(error.message);
  }

  if (face.style) {
    $('style-label').textContent = face.style.label;
    style = face.style.defaultValue;
    buildChips($('style-chips'), face.style.options, style, value => { style = value; render(); });
    $('style-group').hidden = false;
  }
  if (face.palette) {
    palette = face.palette.defaultValue;
    buildChips($('palette-chips'), face.palette.options, palette, value => { palette = value; render(); }, true);
    $('palette-group').hidden = false;
  }

  timeChips.addEventListener('click', event => {
    const button = event.target.closest('button[data-time]');
    if (button) setTime(button.dataset.time);
  });
  timeInput.addEventListener('change', () => { if (timeInput.value) setTime(timeInput.value); });

  controls.hidden = false;
  readout.hidden = false;
  tick();
  setInterval(tick, 250);
  await render();
}

function buildChips(container, options, selected, onSelect, swatches = false) {
  container.innerHTML = options.map(o => {
    const swatch = swatches && o.colors.length
      ? `<i class="swatch" style="--a:${o.colors[0]};--b:${o.colors[1] || o.colors[0]}"></i>` : '';
    return `<button type="button" data-value="${escapeHtml(o.id)}">${swatch}${escapeHtml(o.label)}</button>`;
  }).join('');
  const mark = value => container.querySelectorAll('button').forEach(b =>
    b.classList.toggle('active', b.dataset.value === value));
  mark(selected);
  container.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button) return;
    mark(button.dataset.value);
    onSelect(button.dataset.value);
  });
}

// "now", or "HH:MM" today; the face animates forward from there.
function setTime(value) {
  if (value === 'now') {
    offset = 0;
    timeInput.value = '';
  } else {
    const [h, m] = value.split(':').map(Number);
    const target = new Date();
    target.setHours(h, m, 0, 0);
    offset = target - Date.now();
    timeInput.value = value;
  }
  timeChips.querySelectorAll('button').forEach(b => b.classList.toggle('active', b.dataset.time === value));
  tick();
}

function tick() {
  const now = new Date(Date.now() + offset);
  clock.textContent = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  clockMode.textContent = offset ? 'Simulated' : 'Live';
  clockMode.classList.toggle('live', !offset);
}

// Re-resolve style and palette into renderer input; the loop picks it up.
async function render() {
  // Hold the frame loop while preparing: tinting palette images is slow when
  // it has to compete with continuous rendering.
  const version = ++prepareVersion;
  paused = true;
  try {
    const prepared = await prepare(face, { style, palette });
    if (version !== prepareVersion) return;
    input = prepared;
    paused = false;
    if (!looping) requestAnimationFrame(loop);
  } catch (error) {
    showPlaceholder(`Render error: ${error.message}`);
  }
}

async function loop() {
  looping = !paused;
  if (paused) return;
  try {
    await renderWatchFaceFrame(canvas, {
      ...input,
      width: 450,
      height: 450,
      ambient: ambientToggle.checked,
    }, performance.now() - startedAt, new Date(Date.now() + offset));
  } catch (error) {
    looping = false;
    return showPlaceholder(`Render error: ${error.message}`);
  }
  // requestAnimationFrame pauses on its own while the tab is hidden.
  if (input) requestAnimationFrame(loop);
  else looping = false;
}

function showPlaceholder(message) {
  input = null;
  canvas.hidden = true;
  controls.hidden = true;
  readout.hidden = true;
  placeholder.hidden = false;
  placeholder.textContent = message;
}

async function loadMetadata() {
  const panel = $('meta-panel');
  try {
    const response = await fetch(`${root}faces/${slug}/face.yaml`);
    if (!response.ok) throw new Error('not found');
    panel.textContent = await response.text();
  } catch {
    panel.textContent = 'No metadata found';
  }
}

init();

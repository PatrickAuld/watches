let faces = [];
let currentFace = null;
let renderResult = null;
let animating = false;

// When served locally (npx serve . from repo root), faces are at ../faces/.
// When deployed to GitHub Pages, the build copies faces/ next to index.html.
// Detect which works by trying to fetch faces.json from both locations.
let facesBase = 'faces';  // default for deployed (flat) layout

const canvas = document.getElementById('watch-canvas');
const facePicker = document.getElementById('face-picker');
const timeInput = document.getElementById('time-input');
const timeModeSelect = document.getElementById('time-mode');
const ambientToggle = document.getElementById('ambient-toggle');
const animateToggle = document.getElementById('animate-toggle');
const quickBtns = document.querySelectorAll('[data-set-time]');
const metaPanel = document.getElementById('meta-panel');
const placeholder = document.getElementById('placeholder');
const canvasEl = document.getElementById('watch-canvas');

async function init() {
  // Detect whether faces/ is a sibling (deployed) or up one level (local dev)
  const localResp = await fetch('../faces/sundial/face.yaml').catch(() => null);
  if (localResp && localResp.ok) {
    facesBase = '../faces';
  }

  const resp = await fetch('faces.json');
  faces = await resp.json();

  facePicker.innerHTML = faces.map(f =>
    `<option value="${f.slug}">${f.name} (${f.status})</option>`
  ).join('');

  // Default time
  timeInput.value = '2026-03-13T10:10';

  facePicker.addEventListener('change', () => loadFace(facePicker.value));
  timeInput.addEventListener('input', () => { timeModeSelect.value = 'fixed'; render(); });
  timeModeSelect.addEventListener('change', render);
  ambientToggle.addEventListener('change', render);
  animateToggle.addEventListener('change', render);
  quickBtns.forEach(btn => btn.addEventListener('click', () => {
    timeInput.value = `2026-03-13T${btn.dataset.setTime}`;
    timeModeSelect.value = 'fixed';
    render();
  }));

  // Load first face that has XML (or just the first one)
  if (faces.length > 0) {
    await loadFace(faces[0].slug);
  }
}

async function loadFace(slug) {
  // Stop any running animation
  if (renderResult && renderResult.stop) {
    renderResult.stop();
    renderResult = null;
  }

  currentFace = faces.find(f => f.slug === slug);
  facePicker.value = slug;

  // Try to fetch XML
  let xml;
  try {
    const resp = await fetch(`${facesBase}/${slug}/watchface.xml`);
    if (!resp.ok) throw new Error(`${resp.status}`);
    xml = await resp.text();
  } catch {
    showPlaceholder(`No watchface.xml for "${slug}" yet`);
    loadMetadata(slug);
    return;
  }

  // Parse XML for image resource references and load them
  const assets = new Map();
  const resourceMatches = xml.matchAll(/resource="([^"]+)"/g);
  for (const match of resourceMatches) {
    const name = match[1];
    if (assets.has(name)) continue;
    try {
      const resp = await fetch(`${facesBase}/${slug}/assets/${name}.png`);
      if (resp.ok) {
        assets.set(name, await resp.arrayBuffer());
      }
    } catch {
      // Asset not found, skip
    }
  }

  currentFace._xml = xml;
  currentFace._assets = assets;

  showCanvas();
  await render();
  loadMetadata(slug);
}

function showPlaceholder(msg) {
  canvasEl.style.display = 'none';
  placeholder.style.display = 'block';
  placeholder.textContent = msg;
}

function showCanvas() {
  canvasEl.style.display = 'block';
  placeholder.style.display = 'none';
}

function getTime() {
  if (timeModeSelect.value === 'live') return new Date();
  return new Date(timeInput.value || '2026-03-13T10:10');
}

async function render() {
  if (!currentFace || !currentFace._xml) return;

  // Stop previous animation
  if (renderResult && renderResult.stop) {
    renderResult.stop();
    renderResult = null;
  }

  const shouldAnimate = animateToggle.checked;
  const ambient = ambientToggle.checked;

  try {
    renderResult = await renderWatchFace(canvas, {
      xml: currentFace._xml,
      assets: currentFace._assets,
      width: 450,
      height: 450,
      time: shouldAnimate ? undefined : getTime(),
      ambient: ambient,
      animate: shouldAnimate,
    });
  } catch (err) {
    showPlaceholder(`Render error: ${err.message}`);
  }
}

async function loadMetadata(slug) {
  try {
    const resp = await fetch(`${facesBase}/${slug}/face.yaml`);
    if (!resp.ok) throw new Error('not found');
    const text = await resp.text();
    metaPanel.innerHTML = `<pre style="white-space:pre-wrap;margin:0;font-size:0.82rem;color:var(--text);font-family:monospace">${escapeHtml(text)}</pre>`;
  } catch {
    metaPanel.innerHTML = '<p style="color:var(--muted)">No metadata found</p>';
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Live mode ticker
setInterval(() => {
  if (timeModeSelect.value === 'live' && !animateToggle.checked) {
    render();
  }
}, 1000);

init();

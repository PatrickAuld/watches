let faces = [];
let currentFace = null;
let renderResult = null;
let animating = false;

const facesBase = 'faces';

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
const canvasEl = document.getElementById('watch-canvas');
let renderVersion = 0;

async function init() {
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
  stylePicker.addEventListener('change', render);
  palettePicker.addEventListener('change', render);
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
  for (const [name, filename] of Object.entries(currentFace.assets)) {
    try {
      const resp = await fetch(`${facesBase}/${slug}/assets/${filename}`);
      if (!resp.ok) throw new Error(`${resp.status}`);
      assets.set(name, await resp.arrayBuffer());
    } catch (error) {
      showPlaceholder(`Missing asset ${filename}: ${error.message}`);
      return;
    }
  }

  currentFace._xml = xml;
  currentFace._assets = assets;
  currentFace._tintedAssets = new Map();
  const doc = new DOMParser().parseFromString(xml, 'application/xml');
  const labels = new Map();
  try {
    const response = await fetch(`${facesBase}/${slug}/strings.xml`);
    if (response.ok) {
      const strings = new DOMParser().parseFromString(await response.text(), 'application/xml');
      for (const el of strings.querySelectorAll('string[name]')) {
        labels.set(el.getAttribute('name'), el.textContent);
      }
    }
  } catch { /* Not every face supplies its own strings. */ }
  const styleConfig = doc.querySelector('UserConfigurations > ListConfiguration');
  const sceneConfig = styleConfig && [...doc.querySelectorAll('Scene ListConfiguration')]
    .find(el => el.getAttribute('id') === styleConfig.getAttribute('id'));
  currentFace._styleConfig = sceneConfig ? styleConfig.getAttribute('id') : null;
  styleCard.hidden = !sceneConfig;
  if (sceneConfig) {
    stylePicker.closest('label').querySelector('span').textContent =
      labels.get(styleConfig.getAttribute('displayName')) || 'Style';
    stylePicker.innerHTML = [...styleConfig.querySelectorAll(':scope > ListOption')].map(opt => {
      const id = opt.getAttribute('id');
      const label = labels.get(opt.getAttribute('displayName')) || id;
      return `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`;
    }).join('');
    stylePicker.value = styleConfig.getAttribute('defaultValue');
  }
  const paletteConfig = doc.querySelector('UserConfigurations > ColorConfiguration');
  currentFace._paletteConfig = paletteConfig?.getAttribute('id');
  paletteCard.hidden = !paletteConfig;
  if (paletteConfig) {
    palettePicker.innerHTML = [...paletteConfig.querySelectorAll(':scope > ColorOption')].map(opt => {
      const id = opt.getAttribute('id');
      const label = labels.get(opt.getAttribute('displayName')) || id;
      return `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`;
    }).join('');
    palettePicker.value = paletteConfig.getAttribute('defaultValue');
  }

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
  const version = ++renderVersion;

  // Stop previous animation
  if (renderResult && renderResult.stop) {
    renderResult.stop();
    renderResult = null;
  }

  const shouldAnimate = animateToggle.checked;
  const ambient = ambientToggle.checked;

  try {
    const doc = new DOMParser().parseFromString(currentFace._xml, 'application/xml');
    if (currentFace._styleConfig) {
      const sceneConfig = [...doc.querySelectorAll('Scene ListConfiguration')]
        .find(el => el.getAttribute('id') === currentFace._styleConfig);
      const option = [...sceneConfig.children].find(el =>
        el.tagName === 'ListOption' && el.getAttribute('id') === stylePicker.value);
      sceneConfig.replaceWith(...[...option.children].map(el => el.cloneNode(true)));
    }
    const assets = new Map(currentFace._assets);
    if (currentFace._paletteConfig) {
      const selected = [...doc.querySelectorAll('UserConfigurations > ColorConfiguration > ColorOption')]
        .find(el => el.getAttribute('id') === palettePicker.value);
      const ink = selected.getAttribute('colors').split(/\s+/)[1];
      for (const part of doc.querySelectorAll('Scene PartImage[tintColor]')) {
        const image = part.querySelector(':scope > Image');
        const source = image.getAttribute('resource');
        const tinted = `${source}_palette_${palettePicker.value}`;
        if (!currentFace._tintedAssets.has(tinted)) {
          currentFace._tintedAssets.set(tinted, await tintImage(currentFace._assets.get(source), ink));
        }
        image.setAttribute('resource', tinted);
        assets.set(tinted, currentFace._tintedAssets.get(tinted));
      }
    }
    if (version !== renderVersion) return;
    const previewXml = new XMLSerializer().serializeToString(doc);
    renderResult = await renderWatchFace(canvas, {
      xml: previewXml,
      assets,
      configuration: currentFace._paletteConfig ? {[currentFace._paletteConfig]: palettePicker.value} : {},
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

async function tintImage(bytes, color) {
  const bitmap = await createImageBitmap(new Blob([bytes]));
  const surface = document.createElement('canvas');
  surface.width = bitmap.width;
  surface.height = bitmap.height;
  const context = surface.getContext('2d');
  context.drawImage(bitmap, 0, 0);
  bitmap.close();
  const pixels = context.getImageData(0, 0, surface.width, surface.height);
  const rgb = color.slice(-6);
  const channels = [0, 2, 4].map(i => parseInt(rgb.slice(i, i + 2), 16));
  for (let i = 0; i < pixels.data.length; i += 4) {
    pixels.data[i] = channels[0];
    pixels.data[i + 1] = channels[1];
    pixels.data[i + 2] = channels[2];
  }
  context.putImageData(pixels, 0, 0);
  const blob = await new Promise(resolve => surface.toBlob(resolve, 'image/png'));
  return blob.arrayBuffer();
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

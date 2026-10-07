import { renderWatchFaceFrame } from './vendor/wff-web.js';
import { loadCatalog, loadFace, prepare } from './render.js';

const root = './';
const thumbs = []; // { canvas, input, visible }
const startedAt = performance.now();
// Per-frame time budget shared by all thumbnails, so a full gallery keeps
// scrolling smoothly: each frame draws as many on-screen faces as fit,
// continuing round-robin from where the last frame stopped.
const BUDGET_MS = 10;
let cursor = 0;
let looping = false;

function draw(thumb) {
  return renderWatchFaceFrame(thumb.canvas, { ...thumb.input, width: 450, height: 450 },
    performance.now() - startedAt, new Date());
}

async function loop() {
  looping = true;
  const visible = thumbs.filter(t => t.visible);
  const deadline = performance.now() + BUDGET_MS;
  for (let drawn = 0; drawn < visible.length; drawn++) {
    const thumb = visible[cursor++ % visible.length];
    try { await draw(thumb); } catch (error) { console.warn(error); }
    if (performance.now() > deadline) break;
  }
  looping = !document.hidden;
  if (looping) requestAnimationFrame(loop);
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden && !looping) requestAnimationFrame(loop);
});

const observer = new IntersectionObserver(entries => {
  for (const { target, isIntersecting } of entries) {
    const thumb = thumbs.find(t => t.canvas === target);
    if (thumb) thumb.visible = isIntersecting;
  }
});

const catalog = await loadCatalog(root);
await Promise.all(catalog.filter(entry => entry.xml).map(async entry => {
  const canvas = document.querySelector(`canvas[data-face="${entry.slug}"]`);
  if (!canvas) return;
  try {
    const thumb = { canvas, input: await prepare(await loadFace(root, entry)), visible: false };
    thumbs.push(thumb);
    observer.observe(canvas);
    await draw(thumb);
  } catch (error) {
    canvas.closest('.thumb').classList.add('thumb-error');
    console.warn(`${entry.slug}: ${error.message}`);
  }
}));
looping = true;
requestAnimationFrame(loop);

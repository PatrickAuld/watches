import { renderWatchFace } from './vendor/wff-web.js';
import { loadCatalog, loadFace, prepare } from './render.js';

const root = './';
const rendered = [];

async function drawThumbnail(canvas, entry) {
  try {
    const face = await loadFace(root, entry);
    const input = await prepare(face);
    const draw = () => renderWatchFace(canvas, { ...input, width: 450, height: 450, time: new Date() });
    await draw();
    rendered.push(draw);
  } catch (error) {
    canvas.closest('.thumb').classList.add('thumb-error');
    console.warn(`${entry.slug}: ${error.message}`);
  }
}

const catalog = await loadCatalog(root);
await Promise.all(catalog.filter(entry => entry.xml).map(entry => {
  const canvas = document.querySelector(`canvas[data-face="${entry.slug}"]`);
  return canvas ? drawThumbnail(canvas, entry) : null;
}));

// Keep thumbnails at the current minute.
setInterval(() => rendered.forEach(draw => draw()), 30000);

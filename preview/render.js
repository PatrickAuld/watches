// Shared loading and XML preparation for the gallery and per-face pages.

export function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export async function loadCatalog(root) {
  const response = await fetch(`${root}faces.json`);
  if (!response.ok) throw new Error(`faces.json: ${response.status}`);
  return response.json();
}

export function faceUrl(root, slug) {
  return `${root}faces/${slug}/`;
}

function parseXml(text) {
  return new DOMParser().parseFromString(text, 'application/xml');
}

function readOptions(config, tag, labels) {
  return [...config.querySelectorAll(`:scope > ${tag}`)].map(option => {
    const id = option.getAttribute('id');
    return { id, label: labels.get(option.getAttribute('displayName')) || id };
  });
}

// Fetch a face's XML, assets, editor labels and user configurations.
export async function loadFace(root, entry) {
  const base = `${root}faces/${entry.slug}`;
  const response = await fetch(`${base}/watchface.xml`);
  if (!response.ok) throw new Error(`watchface.xml: ${response.status}`);
  const xml = await response.text();

  const assets = new Map();
  await Promise.all(Object.entries(entry.assets).map(async ([name, filename]) => {
    const asset = await fetch(`${base}/assets/${filename}`);
    if (!asset.ok) throw new Error(`Missing asset ${filename}: ${asset.status}`);
    assets.set(name, await asset.arrayBuffer());
  }));

  const labels = new Map();
  try {
    const strings = await fetch(`${base}/strings.xml`);
    if (strings.ok) {
      for (const el of parseXml(await strings.text()).querySelectorAll('string[name]')) {
        labels.set(el.getAttribute('name'), el.textContent);
      }
    }
  } catch { /* Not every face supplies its own strings. */ }

  const doc = parseXml(xml);
  let style = null;
  const styleConfig = doc.querySelector('UserConfigurations > ListConfiguration');
  const sceneConfig = styleConfig && [...doc.querySelectorAll('Scene ListConfiguration')]
    .find(el => el.getAttribute('id') === styleConfig.getAttribute('id'));
  if (sceneConfig) {
    style = {
      id: styleConfig.getAttribute('id'),
      label: labels.get(styleConfig.getAttribute('displayName')) || 'Style',
      defaultValue: styleConfig.getAttribute('defaultValue'),
      options: readOptions(styleConfig, 'ListOption', labels),
    };
  }

  let palette = null;
  const paletteConfig = doc.querySelector('UserConfigurations > ColorConfiguration');
  if (paletteConfig) {
    palette = {
      id: paletteConfig.getAttribute('id'),
      defaultValue: paletteConfig.getAttribute('defaultValue'),
      options: readOptions(paletteConfig, 'ColorOption', labels),
    };
  }

  return { slug: entry.slug, xml, assets, labels, style, palette, tinted: new Map() };
}

// Resolve the selected style and palette into renderer input.
export async function prepare(face, { style, palette } = {}) {
  const doc = parseXml(face.xml);
  const assets = new Map(face.assets);
  const configuration = {};

  if (face.style) {
    const selected = style || face.style.defaultValue;
    const sceneConfig = [...doc.querySelectorAll('Scene ListConfiguration')]
      .find(el => el.getAttribute('id') === face.style.id);
    const option = [...sceneConfig.children].find(el =>
      el.tagName === 'ListOption' && el.getAttribute('id') === selected);
    sceneConfig.replaceWith(...[...option.children].map(el => el.cloneNode(true)));
  }

  if (face.palette) {
    const selected = palette || face.palette.defaultValue;
    configuration[face.palette.id] = selected;
    const option = [...doc.querySelectorAll('UserConfigurations > ColorConfiguration > ColorOption')]
      .find(el => el.getAttribute('id') === selected);
    const ink = option.getAttribute('colors').split(/\s+/)[1];
    for (const part of doc.querySelectorAll('Scene PartImage[tintColor]')) {
      const image = part.querySelector(':scope > Image');
      const source = image.getAttribute('resource');
      const tinted = `${source}_palette_${selected}`;
      if (!face.tinted.has(tinted)) {
        face.tinted.set(tinted, await tintImage(face.assets.get(source), ink));
      }
      image.setAttribute('resource', tinted);
      assets.set(tinted, face.tinted.get(tinted));
    }
  }

  return { xml: new XMLSerializer().serializeToString(doc), assets, configuration };
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

const PIXEL_WATCH_PROFILE = {
  id: 'google-pixel-watch',
  name: 'Google Pixel Watch',
  shape: 'round',
  baseResolution: 450,
  safeInset: 24,
};

function polarToCartesian(cx, cy, r, degrees) {
  const radians = ((degrees - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(radians),
    y: cy + r * Math.sin(radians),
  };
}

function getWatchTime(state) {
  if (state.mode === 'live') return new Date();
  if (state.fixedTime) return new Date(state.fixedTime);
  return new Date();
}

function formatTimeForInput(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function hourDegrees(date) {
  return (date.getHours() % 12) * 30 + date.getMinutes() * 0.5;
}

function minuteDegrees(date) {
  return date.getMinutes() * 6 + date.getSeconds() * 0.1;
}

function secondDegrees(date) {
  return date.getSeconds() * 6;
}

function watchFrame(innerHtml, opts = {}) {
  return `
    <div class="watch-frame">
      <div class="watch-screen" aria-label="${opts.ariaLabel || 'Watch preview'}">
        ${innerHtml}
        <div class="watch-safe-ring"></div>
      </div>
    </div>
  `;
}

function buildTicks(count, r1, r2, stroke, strokeWidth) {
  const cx = 225;
  const cy = 225;
  return Array.from({ length: count }, (_, i) => {
    const angle = (360 / count) * i;
    const a = polarToCartesian(cx, cy, r1, angle);
    const b = polarToCartesian(cx, cy, r2, angle);
    return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" />`;
  }).join('');
}

function renderAtlas(state) {
  const date = getWatchTime(state);
  const h = hourDegrees(date);
  const m = minuteDegrees(date);
  const s = secondDegrees(date);
  const ambient = state.previewMode === 'ambient';
  const hourText = date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const dateText = date.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase();

  return `
    <svg viewBox="0 0 450 450" role="img" aria-label="Atlas prototype watch face">
      <defs>
        <linearGradient id="atlasBg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#12151d" />
          <stop offset="100%" stop-color="#050608" />
        </linearGradient>
      </defs>
      <rect width="450" height="450" fill="url(#atlasBg)" rx="225" />
      <circle cx="225" cy="225" r="186" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="2" />
      <circle cx="225" cy="225" r="164" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1" />
      ${buildTicks(60, 178, 188, 'rgba(255,255,255,0.25)', 2)}
      ${buildTicks(12, 164, 188, '#d6d9e0', 4)}

      <text x="225" y="122" text-anchor="middle" fill="#d4d9e8" font-size="22" font-family="Inter, sans-serif" letter-spacing="4">ATLAS</text>
      <text x="225" y="330" text-anchor="middle" fill="#95a0b8" font-size="18" font-family="Inter, sans-serif" letter-spacing="3">${dateText}</text>
      <text x="225" y="252" text-anchor="middle" fill="#f7f8fa" font-size="52" font-family="Inter, sans-serif" font-weight="600">${hourText}</text>

      <line x1="225" y1="225" x2="225" y2="128" stroke="#f2f4f8" stroke-width="9" stroke-linecap="round" transform="rotate(${h} 225 225)" />
      <line x1="225" y1="225" x2="225" y2="88" stroke="#a8b9d8" stroke-width="5" stroke-linecap="round" transform="rotate(${m} 225 225)" />
      ${ambient ? '' : `<line x1="225" y1="238" x2="225" y2="70" stroke="#7db0ff" stroke-width="2.5" stroke-linecap="round" transform="rotate(${s} 225 225)" />`}
      <circle cx="225" cy="225" r="8" fill="#f4f6fb" />
      <circle cx="225" cy="225" r="4" fill="#6da2ff" />
    </svg>
  `;
}

const faceRegistry = {
  atlas: {
    id: 'atlas',
    name: 'Atlas',
    status: 'prototype',
    route: './faces/atlas.html',
    render: renderAtlas,
  },
};

function bindHomePage() {
  const host = document.getElementById('face-list');
  if (!host) return;
  host.innerHTML = Object.values(faceRegistry).map((face) => `
    <li>
      <a class="face-link" href="${face.route}">
        <span>
          <strong>${face.name}</strong><br />
          <span style="color: var(--muted)">${face.id}</span>
        </span>
        <span class="badge">${face.status}</span>
      </a>
    </li>
  `).join('');
}

function bindFacePage() {
  const root = document.getElementById('prototype-root');
  if (!root) return;

  const faceId = root.dataset.faceId;
  const face = faceRegistry[faceId];
  if (!face) return;

  const state = {
    mode: 'fixed',
    fixedTime: '2026-03-13T10:10',
    previewMode: 'interactive',
  };

  const preview = document.getElementById('watch-preview');
  const fixedTimeInput = document.getElementById('fixed-time');
  const modeInput = document.getElementById('time-mode');
  const previewModeInput = document.getElementById('preview-mode');
  const quickButtons = Array.from(document.querySelectorAll('[data-set-time]'));
  const metaFaceName = document.getElementById('meta-face-name');
  const metaFaceSlug = document.getElementById('meta-face-slug');
  const metaDevice = document.getElementById('meta-device');
  const metaResolution = document.getElementById('meta-resolution');

  fixedTimeInput.value = state.fixedTime;
  modeInput.value = state.mode;
  previewModeInput.value = state.previewMode;
  metaFaceName.textContent = face.name;
  metaFaceSlug.textContent = face.id;
  metaDevice.textContent = PIXEL_WATCH_PROFILE.name;
  metaResolution.textContent = `${PIXEL_WATCH_PROFILE.baseResolution} × ${PIXEL_WATCH_PROFILE.baseResolution}`;

  const render = () => {
    const markup = face.render(state);
    preview.innerHTML = watchFrame(markup, { ariaLabel: `${face.name} watch face preview` });
    if (state.mode === 'live') {
      fixedTimeInput.value = formatTimeForInput(new Date());
    }
  };

  fixedTimeInput.addEventListener('input', (event) => {
    state.fixedTime = event.target.value;
    state.mode = 'fixed';
    modeInput.value = 'fixed';
    render();
  });

  modeInput.addEventListener('change', (event) => {
    state.mode = event.target.value;
    render();
  });

  previewModeInput.addEventListener('change', (event) => {
    state.previewMode = event.target.value;
    render();
  });

  quickButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const timeValue = button.dataset.setTime;
      if (!timeValue) return;
      state.fixedTime = `2026-03-13T${timeValue}`;
      state.mode = 'fixed';
      modeInput.value = 'fixed';
      fixedTimeInput.value = state.fixedTime;
      render();
    });
  });

  render();
  setInterval(() => {
    if (state.mode === 'live') render();
  }, 1000);
}

window.addEventListener('DOMContentLoaded', () => {
  bindHomePage();
  bindFacePage();
});

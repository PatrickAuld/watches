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

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function lineCircleIntersection(angleDegrees, radius) {
  const radians = ((angleDegrees - 90) * Math.PI) / 180;
  return {
    x: 225 + radius * Math.cos(radians),
    y: 225 + radius * Math.sin(radians),
  };
}

function toJulianDate(date) {
  return date.getTime() / 86400000 + 2440587.5;
}

function getSunPosition(date, latitude, longitude) {
  const rad = Math.PI / 180;
  const deg = 180 / Math.PI;
  const jd = toJulianDate(date);
  const t = (jd - 2451545.0) / 36525.0;

  const l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360;
  const m = 357.52911 + t * (35999.05029 - 0.0001537 * t);
  const e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);

  const c = Math.sin(m * rad) * (1.914602 - t * (0.004817 + 0.000014 * t))
    + Math.sin(2 * m * rad) * (0.019993 - 0.000101 * t)
    + Math.sin(3 * m * rad) * 0.000289;

  const trueLong = l0 + c;
  const omega = 125.04 - 1934.136 * t;
  const lambda = trueLong - 0.00569 - 0.00478 * Math.sin(omega * rad);

  const epsilon0 = 23 + (26 + ((21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60)) / 60;
  const epsilon = epsilon0 + 0.00256 * Math.cos(omega * rad);

  const decl = Math.asin(Math.sin(epsilon * rad) * Math.sin(lambda * rad));

  const y = Math.tan((epsilon * rad) / 2);
  const y2 = y * y;
  const eqTime = 4 * deg * (
    y2 * Math.sin(2 * l0 * rad)
    - 2 * e * Math.sin(m * rad)
    + 4 * e * y2 * Math.sin(m * rad) * Math.cos(2 * l0 * rad)
    - 0.5 * y2 * y2 * Math.sin(4 * l0 * rad)
    - 1.25 * e * e * Math.sin(2 * m * rad)
  );

  const utcMinutes = date.getUTCHours() * 60 + date.getUTCMinutes() + date.getUTCSeconds() / 60;
  const trueSolarTime = (utcMinutes + eqTime + 4 * longitude) % 1440;
  const tst = trueSolarTime < 0 ? trueSolarTime + 1440 : trueSolarTime;

  let hourAngle = tst / 4 - 180;
  if (hourAngle < -180) hourAngle += 360;

  const latRad = latitude * rad;
  const haRad = hourAngle * rad;
  const cosZenith = clamp(Math.sin(latRad) * Math.sin(decl) + Math.cos(latRad) * Math.cos(decl) * Math.cos(haRad), -1, 1);
  const zenith = Math.acos(cosZenith);
  const elevation = 90 - zenith * deg;

  const azimuth = (Math.atan2(Math.sin(haRad), Math.cos(haRad) * Math.sin(latRad) - Math.tan(decl) * Math.cos(latRad)) * deg + 180) % 360;

  return { azimuth, elevation };
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

function renderSundial(state) {
  const date = getWatchTime(state);
  const ambient = state.previewMode === 'ambient';
  const hourAngle = hourDegrees(date);
  const sun = getSunPosition(date, 37.7652, -122.2416);
  const sunAngle = sun.azimuth;
  const radius = 198;
  const hourPoint = lineCircleIntersection(hourAngle, 182);
  const sunPoint = lineCircleIntersection(sunAngle, 182);

  const clockwiseDelta = (sunAngle - hourAngle + 360) % 360;
  const ccwDelta = (hourAngle - sunAngle + 360) % 360;
  const bottomAngle = 180;
  const bottomInClockwise = ((bottomAngle - hourAngle + 360) % 360) <= clockwiseDelta;
  const sweepFlag = bottomInClockwise ? 1 : 0;
  const arcSpan = bottomInClockwise ? clockwiseDelta : ccwDelta;
  const largeArcFlag = arcSpan > 180 ? 1 : 0;
  const shadowPath = `M ${hourPoint.x} ${hourPoint.y} A ${radius} ${radius} 0 ${largeArcFlag} ${sweepFlag} ${sunPoint.x} ${sunPoint.y} L ${hourPoint.x} ${hourPoint.y} Z`;

  const hourMarkers = Array.from({ length: 12 }, (_, i) => {
    const angle = i * 30;
    const outer = polarToCartesian(225, 225, 188, angle);
    const inner = polarToCartesian(225, 225, angle % 90 === 0 ? 174 : 179, angle);
    return `
      <line x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" stroke="rgba(66,52,29,0.34)" stroke-width="${angle % 90 === 0 ? 2.6 : 1.6}" stroke-linecap="round" />
    `;
  }).join('');

  return `
    <svg viewBox="0 0 450 450" role="img" aria-label="Sundial prototype watch face">
      <defs>
        <linearGradient id="sundialLight" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#f8efd8" />
          <stop offset="100%" stop-color="#ead2a1" />
        </linearGradient>
        <linearGradient id="sundialShadowFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#755633" stop-opacity="0.48" />
          <stop offset="100%" stop-color="#2f2317" stop-opacity="0.88" />
        </linearGradient>
        <linearGradient id="shadowEdge" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#fff7e7" stop-opacity="0.46" />
          <stop offset="100%" stop-color="#fff7e7" stop-opacity="0.08" />
        </linearGradient>
        <clipPath id="dialClip">
          <circle cx="225" cy="225" r="198" />
        </clipPath>
      </defs>

      <rect width="450" height="450" fill="#110f0b" rx="225" />
      <circle cx="225" cy="225" r="210" fill="#2e2418" />
      <circle cx="225" cy="225" r="203" fill="#c79f61" opacity="0.36" />
      <circle cx="225" cy="225" r="198" fill="url(#sundialLight)" />

      <g clip-path="url(#dialClip)">
        <path d="${shadowPath}" fill="url(#sundialShadowFill)" />
        <path d="${shadowPath}" fill="rgba(24,18,12,0.16)" transform="translate(0 12)" />
        <line x1="${hourPoint.x}" y1="${hourPoint.y}" x2="${sunPoint.x}" y2="${sunPoint.y}" stroke="url(#shadowEdge)" stroke-width="4.5" stroke-linecap="round" />
      </g>

      <circle cx="225" cy="225" r="198" fill="none" stroke="rgba(74,52,18,0.34)" stroke-width="2" />
      <circle cx="225" cy="225" r="184" fill="none" stroke="rgba(255,248,232,0.16)" stroke-width="1" />
      ${hourMarkers}

      <circle cx="${hourPoint.x}" cy="${hourPoint.y}" r="10" fill="${ambient ? '#efe4cb' : '#fff8ea'}" stroke="#60461d" stroke-width="2.5" />
    </svg>
  `;
}

function renderChromeTRex(state) {
  const date = getWatchTime(state);
  const h = hourDegrees(date);
  const m = minuteDegrees(date);
  const s = secondDegrees(date);
  const ambient = state.previewMode === 'ambient';

  const hourMarkers = [
    { angle: 0, type: 'rect', width: 16, height: 34 },
    { angle: 30, type: 'triangle' },
    { angle: 60, type: 'rect', width: 14, height: 24 },
    { angle: 90, type: 'rect', width: 18, height: 38 },
    { angle: 120, type: 'rect', width: 14, height: 24 },
    { angle: 150, type: 'rect', width: 14, height: 24 },
    { angle: 180, type: 'rect', width: 18, height: 38 },
    { angle: 210, type: 'rect', width: 14, height: 24 },
    { angle: 240, type: 'rect', width: 14, height: 24 },
    { angle: 270, type: 'rect', width: 18, height: 38 },
    { angle: 300, type: 'rect', width: 14, height: 24 },
    { angle: 330, type: 'rect', width: 14, height: 24 },
  ];

  const bezelNumerals = [
    { value: '50', angle: 330 },
    { value: '40', angle: 270 },
    { value: '30', angle: 210 },
    { value: '20', angle: 150 },
  ].map(({ value, angle }) => {
    const p = polarToCartesian(225, 225, 182, angle);
    return `<text x="${p.x}" y="${p.y + 12}" text-anchor="middle" fill="#f1f2f4" font-size="32" font-family="Inter, sans-serif" font-weight="600" transform="rotate(${angle - 90} ${p.x} ${p.y})">${value}</text>`;
  }).join('');

  const bezelTicks = Array.from({ length: 15 }, (_, i) => {
    const angle = i * 6;
    const outer = polarToCartesian(225, 225, 214, angle);
    const inner = polarToCartesian(225, 225, i % 3 === 0 ? 194 : 199, angle);
    return `<line x1="${inner.x}" y1="${inner.y}" x2="${outer.x}" y2="${outer.y}" stroke="#f1f2f4" stroke-width="${i % 3 === 0 ? 4 : 2.5}" stroke-linecap="round" />`;
  }).join('');

  const markerSvg = hourMarkers.map((marker) => {
    const center = polarToCartesian(225, 225, 138, marker.angle);
    if (marker.type === 'triangle') {
      return `<g transform="rotate(${marker.angle} ${center.x} ${center.y}) translate(${center.x} ${center.y})">
        <path d="M -18 14 L 0 -18 L 18 14 Z" fill="#f4f5f2" />
      </g>`;
    }
    return `<g transform="rotate(${marker.angle} ${center.x} ${center.y}) translate(${center.x} ${center.y})">
      <rect x="${-marker.width / 2}" y="${-marker.height / 2}" width="${marker.width}" height="${marker.height}" rx="2" fill="#f4f5f2" />
    </g>`;
  }).join('');

  return `
    <svg viewBox="0 0 450 450" role="img" aria-label="ChromeTRex prototype watch face">
      <defs>
        <linearGradient id="chromeRing" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#5e6369" />
          <stop offset="25%" stop-color="#cfd4d9" />
          <stop offset="50%" stop-color="#7a7f87" />
          <stop offset="75%" stop-color="#d7dbe0" />
          <stop offset="100%" stop-color="#4d5258" />
        </linearGradient>
        <radialGradient id="dialGlow" cx="50%" cy="42%" r="72%">
          <stop offset="0%" stop-color="#151619" />
          <stop offset="100%" stop-color="#020202" />
        </radialGradient>
      </defs>

      <rect width="450" height="450" fill="#000" rx="225" />
      <circle cx="225" cy="225" r="223" fill="#0b0b0c" />
      <circle cx="225" cy="225" r="221" fill="url(#chromeRing)" />
      <circle cx="225" cy="225" r="206" fill="#0a0a0b" />
      <circle cx="225" cy="225" r="197" fill="#050505" stroke="#8b9098" stroke-width="1.2" opacity="0.55" />
      ${bezelNumerals}
      <rect x="217" y="19" width="16" height="44" rx="4" fill="#f2f3f5" />
      <line x1="62" y1="132" x2="92" y2="115" stroke="#f2f3f5" stroke-width="7" stroke-linecap="round" />
      <line x1="62" y1="318" x2="92" y2="335" stroke="#f2f3f5" stroke-width="7" stroke-linecap="round" />
      ${bezelTicks}

      <circle cx="225" cy="225" r="164" fill="url(#dialGlow)" stroke="#24272d" stroke-width="2.5" />
      <circle cx="225" cy="225" r="151" fill="none" stroke="#4a4e56" stroke-width="1.5" />
      ${buildTicks(60, 151, 157, '#d1d5dc', 1.7)}
      ${markerSvg}

      <text x="225" y="126" text-anchor="middle" fill="#f3f4f6" font-size="24" font-family="Georgia, serif" font-weight="700">Chrome</text>
      <text x="225" y="148" text-anchor="middle" fill="#f3f4f6" font-size="16" font-family="Georgia, serif">TRex</text>

      <g transform="translate(225 304) scale(1.05)">
        <path d="M -11 7 L -5 4 L -5 -4 L 3 -4 L 7 -11 L 12 -11 L 12 -7 L 15 -7 L 15 -3 L 12 -3 L 12 4 L 8 4 L 8 8 L 5 8 L 5 11 L 1 11 L 1 6 L -3 6 L -7 11 L -11 11 L -8 6 L -13 3 L -13 -1 L -11 -1 L -11 7 Z" fill="#f3f4f6" />
      </g>
      <text x="225" y="338" text-anchor="middle" fill="#d6d9de" font-size="10" font-family="Inter, sans-serif" letter-spacing="3">PIXEL MADE</text>

      <g transform="rotate(${h} 225 225)">
        <path d="M 213 225 L 225 121 L 237 225 L 225 240 Z" fill="#f3f4f2" stroke="#d1d2cf" stroke-width="1.3" />
        <rect x="218" y="118" width="14" height="18" rx="2" fill="#f3f4f2" />
      </g>
      <g transform="rotate(${m} 225 225)">
        <path d="M 219 236 L 221 152 L 225 78 L 229 152 L 231 236 Z" fill="#f7f7f4" stroke="#d1d2cf" stroke-width="1" />
        <rect x="219" y="74" width="12" height="14" rx="2.5" fill="#f7f7f4" />
      </g>
      ${ambient ? '' : `<g transform="rotate(${s} 225 225)"><line x1="225" y1="241" x2="225" y2="86" stroke="#f3f4f6" stroke-width="2" stroke-linecap="round" /><circle cx="225" cy="152" r="5" fill="#f3f4f6" /></g>`}
      <circle cx="225" cy="225" r="7" fill="#0f1011" stroke="#2d3138" stroke-width="2" />
      <circle cx="225" cy="225" r="3" fill="#ffffff" />
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
  'chrome-trex': {
    id: 'chrome-trex',
    name: 'ChromeTRex',
    status: 'prototype',
    route: './faces/chrome-trex.html',
    render: renderChromeTRex,
  },
  sundial: {
    id: 'sundial',
    name: 'Sundial',
    status: 'prototype',
    route: './faces/sundial.html',
    render: renderSundial,
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

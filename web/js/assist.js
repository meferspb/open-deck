/**
 * Ассистент посадки и руления: опрос статуса и команды.
 *
 * Вся логика контуров живёт на шлюзе; страница только показывает состояние
 * и отправляет действия. Никаких внешних ресурсов и таймеров с тяжёлой
 * работой: 1–2 запроса в секунду по локальной сети.
 */

import { hydrateDonationLinks } from './core/donation-links.js';
import { initI18n, onLocaleChange, t } from './core/i18n.js';

initI18n();

const $ = (id) => document.getElementById(id);

const PHASES = {
  off: 'assist.phase.off',
  armed: 'assist.phase.armed',
  approach: 'assist.phase.approach',
  flare: 'assist.phase.flare',
  rollout: 'assist.phase.rollout',
  done: 'assist.phase.done',
  toga: 'assist.phase.toga',
};

let status = null;
let draggingSpeed = false;
let warningTimer = null;
let pollTimer = null;
let lastLinkState = 'noData';

function setLink(state, text) {
  const link = $('assist-link');
  lastLinkState = state;
  link.dataset.state = state;
  link.textContent = text;
}

function showWarning(text) {
  const box = $('assist-warning');
  box.textContent = text;
  box.hidden = false;
  clearTimeout(warningTimer);
  warningTimer = setTimeout(() => {
    box.hidden = true;
  }, 6000);
}

function fmt(value, digits = 0, unit = '') {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return `${value.toFixed(digits)}${unit}`;
}

function phaseLabel(value) {
  const key = String(value || 'off');
  return PHASES[key] ? t(PHASES[key]) : key;
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...options,
  });
  if (response.status === 401) {
    const next = window.location.pathname + window.location.search;
    window.location.replace(`/login.html?next=${encodeURIComponent(next)}`);
    const error = new Error(t('assist.warning.loginRequired'));
    error.code = 'login_required';
    throw error;
  }
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(t('assist.warning.nonJson'));
    }
  }
  if (!response.ok) {
    throw new Error(data?.message ?? data?.error ?? `HTTP ${response.status}`);
  }
  return data;
}

function render(next) {
  status = next;
  const telemetry = next.telemetry || {};
  const taxi = next.taxi || {};
  const landing = next.landing || {};

  const landingBadge = $('landing-phase');
  landingBadge.dataset.phase = landing.phase || 'off';
  landingBadge.textContent = phaseLabel(landing.phase);
  $('landing-message').textContent = landing.message || t('assist.landing.message');

  $('l-ra').textContent = fmt(telemetry.radioAltitudeFt, 0, ' ft');
  $('l-ias').textContent = fmt(telemetry.iasKt, 0, ' kt');
  $('l-vs').textContent = fmt(telemetry.verticalSpeedFpm, 0, ' fpm');
  $('l-loc').textContent = telemetry.locValid
    ? fmt(telemetry.localizerDeg, 2, '°')
    : '—';
  $('l-gs').textContent = telemetry.gsValid
    ? fmt(telemetry.glideSlopeDeg, 2, '°')
    : '—';
  $('l-ap').textContent = `${telemetry.autopilotMaster ? 'AP' : '—'} / ${telemetry.approach ? 'APR' : '—'}`;

  const taxiBadge = $('taxi-phase');
  taxiBadge.dataset.phase = taxi.engaged ? 'engaged' : 'off';
  taxiBadge.textContent = taxi.engaged ? t('assist.taxi.engaged') : t('assist.taxi.off');
  $('taxi-message').textContent = taxi.message || t('assist.taxi.message');

  $('t-gs').textContent = fmt(telemetry.groundSpeedKt, 1, ' kt');
  $('t-hdg').textContent = fmt(telemetry.headingDeg, 0, '°');
  $('t-thr').textContent = fmt(taxi.throttlePct, 1, ' %');
  $('t-rud').textContent = fmt(taxi.rudderPct, 1, ' %');
  $('t-target').textContent = `${fmt(taxi.targetSpeedKt, 0)} kt · ${fmt(taxi.targetHeadingDeg, 0)}°`;
  $('t-brake').textContent = telemetry.parkingBrake === true
    ? t('assist.brake.parking')
    : telemetry.parkingBrake === false
      ? t('assist.brake.released')
      : '—';

  $('taxi-heading').textContent = fmt(taxi.targetHeadingDeg, 0, '°');

  const speed = $('taxi-speed');
  const limits = next.limits || {};
  if (limits.taxiSpeedMinKt) speed.min = String(limits.taxiSpeedMinKt);
  if (limits.taxiSpeedMaxKt) speed.max = String(limits.taxiSpeedMaxKt);
  if (!draggingSpeed && typeof taxi.targetSpeedKt === 'number') {
    speed.value = String(Math.round(taxi.targetSpeedKt));
    $('taxi-speed-value').textContent = String(Math.round(taxi.targetSpeedKt));
  }

  const landingActive = Boolean(landing.active);
  $('landing-arm').disabled = landingActive || telemetry.onGround === true || telemetry.onGround == null;
  $('landing-disarm').disabled = !landingActive;
  $('taxi-engage').disabled = Boolean(taxi.engaged) || !telemetry.onGround;
  $('taxi-disengage').disabled = !taxi.engaged;
}

async function refresh() {
  try {
    const next = await request('/api/assist');
    render(next);
    setLink('online', t('assist.link.online'));
  } catch (error) {
    setLink('offline', t('assist.link.offline'));
    if (error?.code === 'login_required') return;
    showWarning(t('assist.warning.status', { message: error.message }));
  }
}

async function action(path, body) {
  try {
    const response = await request(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (response?.status) render(response.status);
    if (response?.message) showWarning(response.message);
  } catch (error) {
    if (error?.code === 'login_required') return;
    showWarning(error.message);
  }
  refresh();
}

function schedulePoll() {
  clearTimeout(pollTimer);
  pollTimer = setTimeout(async () => {
    await refresh();
    schedulePoll();
  }, 700);
}

onLocaleChange(() => {
  if (status) render(status);
  const linkKey = lastLinkState === 'online'
    ? 'assist.link.online'
    : lastLinkState === 'offline'
      ? 'assist.link.offline'
      : 'assist.link.noData';
  setLink(lastLinkState, t(linkKey));
});

$('landing-arm').addEventListener('click', () => action('/api/assist/landing', { action: 'arm' }));
$('landing-disarm').addEventListener('click', () =>
  action('/api/assist/landing', { action: 'disarm' }),
);
$('landing-toga').addEventListener('click', () => action('/api/assist/landing', { action: 'toga' }));
$('landing-nav').addEventListener('click', () =>
  action('/api/assist/landing', { action: 'nav_only' }),
);

$('taxi-engage').addEventListener('click', () => action('/api/assist/taxi', { action: 'engage' }));
$('taxi-disengage').addEventListener('click', () =>
  action('/api/assist/taxi', { action: 'disengage' }),
);
$('taxi-stop').addEventListener('click', () => action('/api/assist/taxi', { action: 'stop' }));

const speed = $('taxi-speed');
speed.addEventListener('pointerdown', () => {
  draggingSpeed = true;
});
speed.addEventListener('pointerup', () => {
  draggingSpeed = false;
});
speed.addEventListener('input', () => {
  $('taxi-speed-value').textContent = speed.value;
});
speed.addEventListener('change', () => {
  draggingSpeed = false;
  action('/api/assist/taxi', { action: 'speed', value: Number(speed.value) });
});

for (const button of document.querySelectorAll('[data-heading]')) {
  button.addEventListener('click', () => {
    const delta = Number(button.dataset.heading);
    action('/api/assist/taxi', { action: 'heading', delta });
  });
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) refresh();
});

hydrateDonationLinks();
refresh();
schedulePoll();

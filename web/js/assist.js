/**
 * Ассистент посадки и руления: опрос статуса и команды.
 *
 * Вся логика контуров живёт на шлюзе; страница только показывает состояние
 * и отправляет действия. Никаких внешних ресурсов и таймеров с тяжёлой
 * работой: 1–2 запроса в секунду по локальной сети.
 */

const $ = (id) => document.getElementById(id);

const PHASES = {
  off: 'выключен',
  armed: 'взведён',
  approach: 'заход',
  flare: 'выравнивание',
  rollout: 'пробег',
  done: 'готово',
  toga: 'TOGA',
};

let status = null;
let draggingSpeed = false;
let warningTimer = null;
let pollTimer = null;

function setLink(state, text) {
  const link = $('assist-link');
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
  return PHASES[key] ?? key;
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
    throw new Error('Требуется вход');
  }
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error('Шлюз вернул ответ не в формате JSON');
    }
  }
  if (!response.ok) {
    throw new Error(data?.message ?? data?.error ?? `HTTP ${response.status}`);
  }
  return data;
}

function render(next) {
  status = next;
  const t = next.telemetry || {};
  const taxi = next.taxi || {};
  const landing = next.landing || {};

  const landingBadge = $('landing-phase');
  landingBadge.dataset.phase = landing.phase || 'off';
  landingBadge.textContent = phaseLabel(landing.phase);
  $('landing-message').textContent =
    landing.message || 'ARM включает автопилот и режим APR.';

  $('l-ra').textContent = fmt(t.radioAltitudeFt, 0, ' ft');
  $('l-ias').textContent = fmt(t.iasKt, 0, ' kt');
  $('l-vs').textContent = fmt(t.verticalSpeedFpm, 0, ' fpm');
  $('l-loc').textContent = `${fmt(t.localizerDeg, 2, '°')}${t.locValid ? '' : ' · нет'}`;
  $('l-gs').textContent = `${fmt(t.glideSlopeDeg, 2, '°')}${t.gsValid ? '' : ' · нет'}`;
  $('l-ap').textContent = `${t.autopilotMaster ? 'AP' : '—'} / ${t.approach ? 'APR' : '—'}`;

  const taxiBadge = $('taxi-phase');
  taxiBadge.dataset.phase = taxi.engaged ? 'engaged' : 'off';
  taxiBadge.textContent = taxi.engaged ? 'включён' : 'выключен';
  $('taxi-message').textContent =
    taxi.message || 'Держит скорость и курс на земле.';

  $('t-gs').textContent = fmt(t.groundSpeedKt, 1, ' kt');
  $('t-hdg').textContent = fmt(t.headingDeg, 0, '°');
  $('t-thr').textContent = fmt(taxi.throttlePct, 1, ' %');
  $('t-rud').textContent = fmt(taxi.rudderPct, 1, ' %');
  $('t-target').textContent = `${fmt(taxi.targetSpeedKt, 0)} kt · ${fmt(taxi.targetHeadingDeg, 0)}°`;
  $('t-brake').textContent =
    t.parkingBrake === true ? 'стояночный' : t.parkingBrake === false ? 'снят' : '—';

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
  $('landing-arm').disabled = landingActive || t.onGround === true || t.onGround == null;
  $('landing-disarm').disabled = !landingActive;
  $('taxi-engage').disabled = Boolean(taxi.engaged) || !t.onGround;
  $('taxi-disengage').disabled = !taxi.engaged;
}

async function refresh() {
  try {
    const next = await request('/api/assist');
    render(next);
    setLink('online', 'на связи');
  } catch (error) {
    setLink('offline', 'нет связи');
    if (String(error?.message || '').includes('Требуется вход')) return;
    showWarning(`Статус недоступен: ${error.message}`);
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
    if (String(error?.message || '').includes('Требуется вход')) return;
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

$('landing-arm').addEventListener('click', () => action('/api/assist/landing', { action: 'arm' }));
$('landing-disarm').addEventListener('click', () =>
  action('/api/assist/landing', { action: 'disarm' }),
);
$('landing-toga').addEventListener('click', () => action('/api/assist/landing', { action: 'toga' }));

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

refresh();
schedulePoll();

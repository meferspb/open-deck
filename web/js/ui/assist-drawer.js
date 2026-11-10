/** Compact landing/taxi assistant drawer for the main instrument page. */
import { t } from '../core/i18n.js';

const PHASES = {
  off: 'assist.phase.off',
  armed: 'assist.phase.armed',
  approach: 'assist.phase.approach',
  flare: 'assist.phase.flare',
  rollout: 'assist.phase.rollout',
  done: 'assist.phase.done',
  toga: 'assist.phase.toga',
};

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  return el;
}

function fmt(value, digits = 0, unit = '') {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(digits)}${unit}`
    : '—';
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    cache: 'no-store',
    ...options,
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch { throw new Error(t('assist.warning.nonJson')); }
  }
  if (!response.ok) throw new Error(data?.message ?? data?.error ?? `HTTP ${response.status}`);
  return data;
}

/**
 * @param {{button: HTMLElement, notify?: (message: string) => void}} options
 */
export function createAssistDrawer({ button, notify }) {
  let status = null;
  let timer = 0;
  let open = false;

  const backdrop = node('div', 'assist-drawer__backdrop');
  backdrop.hidden = true;
  const drawer = node('aside', 'assist-drawer');
  drawer.hidden = true;
  drawer.setAttribute('aria-label', t('assist.heading'));

  const head = node('header', 'assist-drawer__head');
  const title = node('strong', 'assist-drawer__title', t('assist.heading'));
  const close = node('button', 'assist-drawer__close', '✕');
  close.type = 'button';
  close.setAttribute('aria-label', t('assist.landing.disarm'));
  head.append(title, close);

  const landingPhase = node('span', 'assist-badge', t('assist.phase.off'));
  const landingMessage = node('p', 'assist-drawer__message', t('assist.landing.message'));
  const landingReadouts = node('div', 'assist-drawer__readouts');
  const lRa = node('span', 'assist-drawer__value', '—');
  const lIas = node('span', 'assist-drawer__value', '—');
  const lLoc = node('span', 'assist-drawer__value', '—');
  const lGs = node('span', 'assist-drawer__value', '—');
  for (const [label, value] of [
    [t('assist.readout.ra'), lRa],
    [t('assist.readout.ias'), lIas],
    [t('assist.readout.loc'), lLoc],
    [t('assist.readout.gs'), lGs],
  ]) {
    const cell = node('div', 'assist-drawer__cell');
    cell.append(node('span', 'assist-drawer__label', label), value);
    landingReadouts.append(cell);
  }
  const landingActions = node('div', 'assist-drawer__actions');
  const arm = node('button', 'assist-btn assist-btn--primary', t('assist.landing.arm'));
  const disarm = node('button', 'assist-btn', t('assist.landing.disarm'));
  const toga = node('button', 'assist-btn assist-btn--danger', t('assist.landing.toga'));
  const navOnly = node('button', 'assist-btn', t('assist.landing.navOnly'));
  for (const [el, action] of [[arm, 'arm'], [disarm, 'disarm'], [toga, 'toga'], [navOnly, 'nav_only']]) {
    el.type = 'button';
    el.addEventListener('click', () => act('/api/assist/landing', action));
    landingActions.append(el);
  }

  const landing = node('section', 'assist-drawer__section');
  const landingHead = node('div', 'assist-drawer__section-head');
  landingHead.append(node('h3', '', t('assist.landing.title')), landingPhase);
  landing.append(landingHead, landingMessage, landingReadouts, landingActions);

  const taxiPhase = node('span', 'assist-badge', t('assist.phase.off'));
  const taxiMessage = node('p', 'assist-drawer__message', t('assist.taxi.message'));
  const taxiReadouts = node('div', 'assist-drawer__readouts');
  const tGs = node('span', 'assist-drawer__value', '—');
  const tHdg = node('span', 'assist-drawer__value', '—');
  for (const [label, value] of [
    [t('assist.readout.gs'), tGs],
    [t('assist.readout.heading'), tHdg],
  ]) {
    const cell = node('div', 'assist-drawer__cell');
    cell.append(node('span', 'assist-drawer__label', label), value);
    taxiReadouts.append(cell);
  }

  const speedWrap = node('label', 'assist-drawer__speed');
  const speed = document.createElement('input');
  speed.type = 'range';
  speed.min = '3';
  speed.max = '25';
  speed.step = '1';
  speed.value = '12';
  const speedValue = node('output', '', '12');
  speedWrap.append(node('span', '', t('assist.taxi.speedLabel')), speed, speedValue);
  speed.addEventListener('input', () => { speedValue.textContent = speed.value; });
  speed.addEventListener('change', () => act('/api/assist/taxi', 'speed', Number(speed.value)));

  const headingRow = node('div', 'assist-drawer__heading');
  for (const delta of [-5, -1, 1, 5]) {
    const b = node('button', 'assist-btn assist-btn--small', `${delta > 0 ? '+' : '−'}${Math.abs(delta)}°`);
    b.type = 'button';
    b.addEventListener('click', () => act('/api/assist/taxi', 'heading', delta));
    headingRow.append(b);
  }
  const taxiActions = node('div', 'assist-drawer__actions');
  const engage = node('button', 'assist-btn assist-btn--primary', t('assist.taxi.engage'));
  const stop = node('button', 'assist-btn assist-btn--danger', t('assist.taxi.stop'));
  for (const [el, action] of [[engage, 'engage'], [stop, 'stop']]) {
    el.type = 'button';
    el.addEventListener('click', () => act('/api/assist/taxi', action));
    taxiActions.append(el);
  }
  const taxi = node('section', 'assist-drawer__section');
  const taxiHead = node('div', 'assist-drawer__section-head');
  taxiHead.append(node('h3', '', t('assist.taxi.title')), taxiPhase);
  taxi.append(taxiHead, taxiMessage, taxiReadouts, speedWrap, headingRow, taxiActions);

  drawer.append(head, landing, taxi);
  const root = node('div', 'assist-drawer-root');
  root.append(backdrop, drawer);
  document.body.append(root);

  function setOpen(next) {
    open = next;
    backdrop.hidden = !next;
    drawer.hidden = !next;
    button.setAttribute('aria-expanded', String(next));
    if (next) {
      refresh();
      schedule();
    } else {
      clearTimeout(timer);
    }
  }

  function render(next) {
    status = next;
    const telemetry = next?.telemetry ?? {};
    const landingState = next?.landing ?? {};
    const taxiState = next?.taxi ?? {};
    landingPhase.textContent = t(PHASES[landingState.phase] ?? 'assist.phase.off');
    landingPhase.dataset.phase = landingState.phase ?? 'off';
    landingMessage.textContent = landingState.message || t('assist.landing.message');
    lRa.textContent = fmt(telemetry.radioAltitudeFt, 0, ' ft');
    lIas.textContent = fmt(telemetry.iasKt, 0, ' kt');
    lLoc.textContent = telemetry.locValid ? fmt(telemetry.localizerDeg, 2, '°') : '—';
    lGs.textContent = telemetry.gsValid ? fmt(telemetry.glideSlopeDeg, 2, '°') : '—';
    taxiPhase.textContent = taxiState.engaged ? t('assist.taxi.engaged') : t('assist.taxi.off');
    taxiPhase.dataset.phase = taxiState.engaged ? 'engaged' : 'off';
    taxiMessage.textContent = taxiState.message || t('assist.taxi.message');
    tGs.textContent = fmt(telemetry.groundSpeedKt, 1, ' kt');
    tHdg.textContent = fmt(telemetry.headingDeg, 0, '°');
    speed.value = String(Math.round(taxiState.targetSpeedKt ?? Number(speed.value)));
    speedValue.textContent = speed.value;
    arm.disabled = Boolean(landingState.active) || telemetry.onGround !== false;
    disarm.disabled = !landingState.active;
    engage.disabled = Boolean(taxiState.engaged) || !telemetry.onGround;
  }

  async function refresh() {
    if (!open) return;
    try { render(await request('/api/assist')); } catch (error) { notify?.(error.message); }
  }

  function schedule() {
    clearTimeout(timer);
    if (!open) return;
    timer = setTimeout(async () => { await refresh(); schedule(); }, 800);
  }

  async function act(path, action, value) {
    try {
      const payload = { action };
      if (value !== undefined) payload.value = value;
      const response = await request(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response?.status) render(response.status);
      if (response?.message) notify?.(response.message);
    } catch (error) {
      notify?.(error.message);
    }
    refresh();
  }

  button.addEventListener('click', () => setOpen(!open));
  close.addEventListener('click', () => setOpen(false));
  backdrop.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && open) setOpen(false);
  });

  return {
    open: () => setOpen(true),
    close: () => setOpen(false),
    get status() { return status; },
  };
}

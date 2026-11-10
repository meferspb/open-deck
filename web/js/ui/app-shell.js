/**
 * Оболочка приложения: верхняя панель, статус-бар, отладка, блокировка.
 * Здесь только DOM — вся логика загрузки живёт в main.js.
 */

import { onLocaleChange, t } from '../core/i18n.js';

const CONNECTION_KEYS = {
  connecting: 'connection.connecting',
  online: 'connection.online',
  reconnecting: 'connection.reconnecting',
  offline: 'connection.offline',
};

/** @param {string} id */
function byId(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(t('error.elementMissing', { id }));
  return element;
}

/**
 * @param {{
 *   onDeviceChange: (id: string) => void,
 *   onAircraftChange: (id: string) => void,
 *   onRetry: () => void,
 *   onLockRetry: () => void,
 * }} handlers
 */
export function createAppShell({ onDeviceChange, onAircraftChange, onRetry, onLockRetry }) {
  const el = {
    aircraftSelect: byId('aircraft-select'),
    deviceSwitch: byId('device-switch'),
    connection: byId('connection'),
    connectionText: byId('connection-text'),
    devtools: byId('devtools'),
    devtoolsToggle: byId('devtools-toggle'),
    devtoolsClose: byId('devtools-close'),
    devtoolsJson: byId('devtools-json'),
    panelState: byId('panel-state'),
    panelStateTitle: byId('panel-state-title'),
    panelStateHint: byId('panel-state-hint'),
    panelRetry: byId('panel-retry'),
    statusProfile: byId('status-profile'),
    statusLayout: byId('status-layout'),
    statusRate: byId('status-rate'),
    statusGateway: byId('status-gateway'),
    statusWasm: byId('status-wasm'),
    lockScreen: byId('lock-screen'),
    lockTitle: byId('lock-title'),
    lockDetail: byId('lock-detail'),
    lockCode: byId('lock-code'),
    lockRetry: byId('lock-retry'),
    toast: byId('toast'),
  };

  const deviceButtons = [...el.deviceSwitch.querySelectorAll('[data-device]')];
  const status = { profileLabel: '', layoutLabel: '', rate: '', gateway: '', wasm: '' };
  /** @type {ReturnType<typeof setTimeout> | null} */
  let toastTimer = null;
  let locked = false;
  /** @type {Array<{id: string, name: string}>} */
  let lastProfiles = [];
  /** @type {string | null} */
  let lastActiveId = null;
  /** @type {{state: string, detail?: string} | null} */
  let connectionInfo = null;
  /** @type {{reason?: string, code?: string} | null} */
  let lockInfo = null;

  function renderProfiles() {
    if (!lastProfiles.length) {
      const option = document.createElement('option');
      option.textContent = t('panel.noProfiles');
      option.disabled = true;
      el.aircraftSelect.replaceChildren(option);
      return;
    }
    const options = lastProfiles.map((profile) => {
      const option = document.createElement('option');
      option.value = profile.id;
      option.textContent = profile.name;
      return option;
    });
    el.aircraftSelect.replaceChildren(...options);
    if (lastActiveId) el.aircraftSelect.value = lastActiveId;
  }

  function renderConnection() {
    if (!connectionInfo) return;
    const { state, detail } = connectionInfo;
    el.connection.dataset.state = state;
    const label = CONNECTION_KEYS[state] ? t(CONNECTION_KEYS[state]) : state;
    el.connectionText.textContent = detail ? `${label} · ${detail}` : label;
    el.connection.title = detail ? `${label}: ${detail}` : label;
  }

  function renderStatus() {
    const keys = {
      profileLabel: 'panel.profileStatus',
      layoutLabel: 'panel.layoutStatus',
      rate: 'panel.rateStatus',
      gateway: 'panel.gatewayStatus',
      wasm: 'panel.wasmStatus',
    };
    const targets = {
      profileLabel: el.statusProfile,
      layoutLabel: el.statusLayout,
      rate: el.statusRate,
      gateway: el.statusGateway,
      wasm: el.statusWasm,
    };
    for (const [field, key] of Object.entries(keys)) {
      const value = status[field];
      if (value) targets[field].textContent = t(key, { value });
    }
  }

  function renderLock() {
    if (!locked || !lockInfo) return;
    el.lockTitle.textContent = t('lock.title');
    el.lockDetail.textContent = lockInfo.reason || t('lock.detailDefault');
    el.lockCode.textContent = lockInfo.code ? t('lock.code', { code: lockInfo.code }) : '';
  }

  onLocaleChange(() => {
    renderProfiles();
    renderConnection();
    renderStatus();
    renderLock();
  });

  // --- события --------------------------------------------------------
  el.aircraftSelect.addEventListener('change', () => {
    if (el.aircraftSelect.value) onAircraftChange(el.aircraftSelect.value);
  });
  for (const button of deviceButtons) {
    button.addEventListener('click', () => onDeviceChange(button.dataset.device));
  }
  el.panelRetry.addEventListener('click', () => onRetry());
  el.lockRetry.addEventListener('click', () => onLockRetry());

  el.devtoolsToggle.addEventListener('click', () => {
    const open = el.devtools.hidden;
    el.devtools.hidden = !open;
    el.devtoolsToggle.setAttribute('aria-pressed', String(open));
  });
  el.devtoolsClose.addEventListener('click', () => {
    el.devtools.hidden = true;
    el.devtoolsToggle.setAttribute('aria-pressed', 'false');
  });

  return {
    /** @param {Array<{id: string, name: string}>} profiles @param {string|null} activeId */
    setProfiles(profiles, activeId) {
      lastProfiles = Array.isArray(profiles) ? profiles : [];
      lastActiveId = activeId;
      renderProfiles();
    },

    /** @param {string} deviceId */
    setDevice(deviceId) {
      for (const button of deviceButtons) {
        button.setAttribute('aria-pressed', String(button.dataset.device === deviceId));
      }
    },

    /** @param {{state: string, detail?: string}} event */
    setConnection({ state, detail }) {
      connectionInfo = { state, detail };
      renderConnection();
    },

    /** @param {Partial<{profileLabel: string, layoutLabel: string, rate: string, gateway: string}>} patch */
    setStatus(patch) {
      Object.assign(status, patch);
      renderStatus();
    },

    /**
     * @param {{visible: boolean, title?: string, hint?: string, retry?: boolean}} state
     */
    setPanelState({ visible, title = '', hint = '', retry = false }) {
      el.panelState.hidden = !visible;
      if (title) el.panelStateTitle.textContent = title;
      el.panelStateHint.textContent = hint;
      el.panelRetry.hidden = !retry;
    },

    /** @param {string} message @param {'info'|'danger'} [tone] @param {number} [ms] */
    showToast(message, tone = 'info', ms = 3600) {
      if (locked) return;
      el.toast.textContent = message;
      el.toast.dataset.tone = tone;
      el.toast.hidden = false;
      if (toastTimer) clearTimeout(toastTimer);
      toastTimer = setTimeout(() => {
        el.toast.hidden = true;
      }, ms);
    },

    /** @param {string} text */
    setDevtoolsJson(text) {
      if (!el.devtools.hidden) el.devtoolsJson.textContent = text;
    },

    /**
     * Блокировка интерфейса по требованию лицензии (целостность донат-блока).
     * @param {boolean} isLocked
     * @param {{reason?: string, code?: string}} [info]
     */
    setLocked(isLocked, info = {}) {
      locked = isLocked;
      lockInfo = isLocked ? info : null;
      document.body.classList.toggle('is-locked', isLocked);
      el.lockScreen.hidden = !isLocked;
      if (isLocked) {
        renderLock();
        el.toast.hidden = true;
        if (el.devtools) el.devtools.hidden = true;
      } else {
        el.lockCode.textContent = '';
      }
    },
  };
}

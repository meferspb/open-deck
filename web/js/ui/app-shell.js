/**
 * Оболочка приложения: верхняя панель, статус-бар, отладка, блокировка.
 * Здесь только DOM — вся логика загрузки живёт в main.js.
 */

const CONNECTION_LABELS = {
  connecting: 'подключение…',
  online: 'телеметрия',
  reconnecting: 'переподключение…',
  offline: 'нет связи',
};

/** @param {string} id */
function byId(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Не найден элемент #${id}`);
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
    lockScreen: byId('lock-screen'),
    lockTitle: byId('lock-title'),
    lockDetail: byId('lock-detail'),
    lockCode: byId('lock-code'),
    lockRetry: byId('lock-retry'),
    toast: byId('toast'),
  };

  const deviceButtons = [...el.deviceSwitch.querySelectorAll('[data-device]')];
  const status = { profileLabel: '', layoutLabel: '', rate: '', gateway: '' };
  /** @type {ReturnType<typeof setTimeout> | null} */
  let toastTimer = null;
  let locked = false;

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
      if (!profiles?.length) {
        const option = document.createElement('option');
        option.textContent = 'нет профилей';
        option.disabled = true;
        el.aircraftSelect.replaceChildren(option);
        return;
      }
      const options = profiles.map((profile) => {
        const option = document.createElement('option');
        option.value = profile.id;
        option.textContent = profile.name;
        return option;
      });
      el.aircraftSelect.replaceChildren(...options);
      if (activeId) el.aircraftSelect.value = activeId;
    },

    /** @param {string} deviceId */
    setDevice(deviceId) {
      for (const button of deviceButtons) {
        button.setAttribute('aria-pressed', String(button.dataset.device === deviceId));
      }
    },

    /** @param {{state: string, detail?: string}} event */
    setConnection({ state, detail }) {
      el.connection.dataset.state = state;
      const label = CONNECTION_LABELS[state] ?? state;
      el.connectionText.textContent = detail ? `${label} · ${detail}` : label;
      el.connection.title = detail ? `${label}: ${detail}` : label;
    },

    /** @param {Partial<{profileLabel: string, layoutLabel: string, rate: string, gateway: string}>} patch */
    setStatus(patch) {
      Object.assign(status, patch);
      if (status.profileLabel) el.statusProfile.textContent = `профиль: ${status.profileLabel}`;
      if (status.layoutLabel) el.statusLayout.textContent = `раскладка: ${status.layoutLabel}`;
      if (status.rate) el.statusRate.textContent = `поток: ${status.rate}`;
      if (status.gateway) el.statusGateway.textContent = `шлюз: ${status.gateway}`;
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
      document.body.classList.toggle('is-locked', isLocked);
      el.lockScreen.hidden = !isLocked;
      if (isLocked) {
        el.lockTitle.textContent = 'Работа приложения заблокирована';
        el.lockDetail.textContent =
          info.reason ||
          'Проверка целостности интерфейса не пройдена. Восстановите файлы клиента и перезапустите шлюз.';
        el.lockCode.textContent = info.code ? `код: ${info.code}` : '';
        el.toast.hidden = true;
        if (el.devtools) el.devtools.hidden = true;
      } else {
        el.lockCode.textContent = '';
      }
    },
  };
}

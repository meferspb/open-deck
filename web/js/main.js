/**
 * Точка входа веб-клиента.
 *
 * Порядок запуска: устройство/раскладка → реквизиты доната → проверка
 * целостности UI → профили с хоста → WebSocket-телеметрия. Любой сбой
 * на этом пути показывается пользователю, а не молча оставляет пустой экран.
 */

import { api, wsUrl } from './core/api.js';
import { createStore } from './core/store.js';
import { createTelemetrySocket } from './core/socket.js';
import { detectDeviceClass, getPreset, shouldUseFrame } from './ui/device.js';
import { createAppShell } from './ui/app-shell.js';
import { createStage } from './ui/stage.js';
import { createPanelView } from './ui/panel-view.js';
import { createDonation } from './ui/donation.js';
import { createConnect } from './ui/connect.js';
import { createComfort } from './ui/comfort.js';
import { verifyUiIntegrity, watchIntegrity } from './ui/integrity.js';

const DEVICE_KEY = 'rud-gateway:device';
const PROFILE_KEY = 'rud-gateway:profile';

const params = new URLSearchParams(window.location.search);
const store = createStore({
  profiles: [],
  profileId: null,
  deviceId: 'tablet-lg',
  telemetry: null,
});

/** @type {ReturnType<typeof createTelemetrySocket> | null} */
let socket = null;
let locked = false;
let started = false;
let telemetryFrames = 0;
let lastDevtoolsAt = 0;
let lastProvider = '';
let lastAircraftTitle = '';
/** После ручного выбора не переключаемся на «авто» несколько секунд. */
let profileLockUntil = 0;
let switchingProfile = false;
/** @type {null | (() => void)} */
let stopWatch = null;

/** @param {string} id */
function byId(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Не найден элемент #${id}`);
  return element;
}

const shell = createAppShell({
  onDeviceChange: (id) => setDevice(id, true),
  onAircraftChange: (id) => {
    selectProfile(id, true).catch((error) => shell.showToast(error.message, 'danger'));
  },
  onRetry: () => {
    start().catch((error) => shell.showToast(error.message, 'danger'));
  },
  onLockRetry: () => {
    retryIntegrity().catch((error) => shell.showToast(error.message, 'danger'));
  },
});

const stage = createStage({
  stage: byId('stage'),
  frame: byId('device-frame'),
  screen: byId('device-screen'),
  panel: byId('panel'),
});

const panelView = createPanelView({
  panel: byId('panel'),
  getState: () => store.get().telemetry,
  command: (key, value) => {
    if (!socket) return Promise.reject(new Error('Нет соединения с шлюзом'));
    return socket.command(key, value);
  },
  notify: (message) => shell.showToast(message, 'danger'),
});

const donation = createDonation({
  chip: byId('donation-badge'),
  dialog: /** @type {HTMLDialogElement} */ (byId('donation-dialog')),
  body: byId('donation-body'),
  closeButton: byId('donation-close'),
});

createConnect({
  button: byId('connect-phone'),
  dialog: /** @type {HTMLDialogElement} */ (byId('connect-dialog')),
  closeButton: byId('connect-close'),
  image: byId('connect-qr'),
  urlField: byId('connect-url'),
  copyButton: byId('connect-copy'),
  altField: byId('connect-alt'),
  listField: byId('connect-list'),
  notify: (message) => shell.showToast(message, 'info'),
});

const comfort = createComfort({
  brightnessButton: byId('brightness-toggle'),
  kioskButton: byId('kiosk-toggle'),
  exitButton: byId('kiosk-exit'),
  onKioskChange: (on) => {
    if (on) {
      stage.setMode('full');
    } else {
      setupMode();
    }
  },
  notify: (message) => shell.showToast(message, 'info'),
});

// ---------------------------------------------------------------------
// Устройство и раскладка
// ---------------------------------------------------------------------
function setupMode() {
  const forced = params.get('frame');
  const useFrame = forced === null ? shouldUseFrame(window) : forced !== '0';
  stage.setMode(useFrame ? 'frame' : 'full');
}

function resolveDeviceId() {
  const fromUrl = params.get('device');
  if (fromUrl && getPreset(fromUrl).id === fromUrl) return fromUrl;

  try {
    const stored = localStorage.getItem(DEVICE_KEY);
    if (stored && getPreset(stored).id === stored) return stored;
  } catch {
    /* localStorage может быть выключен в приватном режиме */
  }
  return detectDeviceClass(window.innerWidth);
}

/**
 * @param {string} id
 * @param {boolean} persist
 */
function setDevice(id, persist = false) {
  const preset = getPreset(id);
  store.set({ deviceId: preset.id });
  shell.setDevice(preset.id);
  stage.setPreset(preset.id);
  panelView.setDeviceClass(preset.id);
  shell.setStatus({ layoutLabel: `${preset.title} · ${preset.width}×${preset.height}` });
  if (persist) {
    try {
      localStorage.setItem(DEVICE_KEY, preset.id);
    } catch {
      /* игнорируем */
    }
  }
}

// ---------------------------------------------------------------------
// Профили
// ---------------------------------------------------------------------
/** @param {Array<{id: string}>} profiles */
function resolveProfileId(profiles) {
  const fromUrl = params.get('profile');
  if (fromUrl && profiles.some((profile) => profile.id === fromUrl)) return fromUrl;

  try {
    const stored = localStorage.getItem(PROFILE_KEY);
    if (stored && profiles.some((profile) => profile.id === stored)) return stored;
  } catch {
    /* игнорируем */
  }
  return profiles[0].id;
}

/**
 * @param {string} id
 * @param {boolean} fromUser
 */
async function selectProfile(id, fromUser) {
  if (switchingProfile) return null;
  switchingProfile = true;
  if (fromUser) profileLockUntil = performance.now() + 5000;

  try {
    const profiles = store.get().profiles ?? [];
    const target = profiles.find((profile) => profile.id === id) ?? profiles[0];
    if (!target) throw new Error('На шлюзе нет доступных профилей');

    shell.setPanelState({ visible: true, title: `Загрузка «${target.name}»…`, hint: '' });
    const profile = await api.getProfile(target.id);

    store.set({ profileId: target.id, profile });
    shell.setProfiles(profiles, target.id);
    panelView.mount(profile);
    shell.setPanelState({ visible: false });
    shell.setStatus({ profileLabel: `${profile.name} · ${profile.widgets?.length ?? 0} приб.` });

    try {
      localStorage.setItem(PROFILE_KEY, target.id);
    } catch {
      /* игнорируем */
    }

    if (fromUser) {
      try {
        await api.selectAircraft(target.id);
      } catch (error) {
        shell.showToast(error.message, 'danger');
      }
    }

    stage.refresh();
    return profile;
  } finally {
    switchingProfile = false;
  }
}

/**
 * Автопереключение на профиль, который шлюз определил по борту в симуляторе.
 * @param {string | undefined} incoming
 */
function followAircraft(incoming) {
  if (!incoming || !started || locked) return;
  if (performance.now() < profileLockUntil) return;

  const current = store.get().profileId;
  if (incoming === current) return;

  const profiles = store.get().profiles ?? [];
  const target = profiles.find((profile) => profile.id === incoming);
  if (!target) return;

  selectProfile(incoming, false)
    .then((profile) => {
      if (!profile) return;
      shell.showToast(`Борт определён автоматически: ${target.name}`, 'info');
      shell.setStatus({
        profileLabel: `${profile.name} · ${profile.widgets?.length ?? 0} приб. · авто`,
      });
    })
    .catch((error) => console.warn('auto profile switch failed', error));
}

// ---------------------------------------------------------------------
// Телеметрия
// ---------------------------------------------------------------------
function connectSocket() {
  if (socket) return;
  socket = createTelemetrySocket({
    url: wsUrl(),
    onStatus: ({ state, detail }) => shell.setConnection({ state, detail }),
    onMessage: handleMessage,
  });
}

/** @param {any} message */
function handleMessage(message) {
  switch (message.type) {
    case 'telemetry': {
      store.set({ telemetry: message });
      telemetryFrames += 1;

      const now = performance.now();
      if (now - lastDevtoolsAt > 500) {
        lastDevtoolsAt = now;
        shell.setDevtoolsJson(JSON.stringify(message, null, 2).slice(0, 12000));
      }

      const provider = message.sim?.provider;
      if (provider && provider !== lastProvider) {
        lastProvider = provider;
        shell.setStatus({ gateway: `${provider} · ${message.sim?.connected ? 'online' : 'offline'}` });
      }
      const title = message.sim?.aircraftTitle;
      if (title && title !== lastAircraftTitle) {
        lastAircraftTitle = title;
        shell.setStatus({
          gateway: `${provider ?? ''} · ${message.sim?.connected ? 'online' : 'offline'} · ${title}`.trim(),
        });
      }

      followAircraft(message.sim?.profileId);
      break;
    }

    case 'hello': {
      if (Array.isArray(message.profiles) && message.profiles.length) {
        store.set({ profiles: message.profiles });
        shell.setProfiles(message.profiles, store.get().profileId);
      }
      if (message.state) {
        store.set({ telemetry: message.state });
      }
      if (message.server) {
        shell.setStatus({
          gateway: `${message.server.name} v${message.server.version} · ${message.state?.sim?.provider ?? ''}`.trim(),
        });
      }
      break;
    }

    case 'profiles': {
      if (Array.isArray(message.profiles) && message.profiles.length) {
        store.set({ profiles: message.profiles });
        shell.setProfiles(message.profiles, store.get().profileId);
      }
      break;
    }

    case 'aircraft': {
      const nextId = message.profileId;
      if (nextId && nextId !== store.get().profileId && started && !locked) {
        selectProfile(nextId, false).catch((error) => console.warn('aircraft switch failed', error));
      }
      break;
    }

    case 'error': {
      shell.showToast(message.error ?? 'Шлюз вернул ошибку', 'danger');
      break;
    }

    default:
      break;
  }
}

setInterval(() => {
  if (locked) return;
  const rate = telemetryFrames;
  telemetryFrames = 0;
  const latency = socket?.latencyMs;
  shell.setStatus({ rate: `${rate} Гц${latency != null ? ` · RTT ${latency} мс` : ''}` });
}, 1000);

// ---------------------------------------------------------------------
// Целостность и блокировка
// ---------------------------------------------------------------------
function installWatch() {
  stopWatch?.();
  stopWatch = watchIntegrity({
    badge: document.querySelector('[data-donation-badge]'),
    onViolation: (reason, code) => lockUi(reason, code),
  });
}

/** @param {string} reason @param {string} code */
function lockUi(reason, code) {
  if (locked) return;
  locked = true;
  started = false;
  socket?.stop();
  socket = null;
  panelView.destroy();
  shell.setLocked(true, { reason, code });
  shell.setConnection({ state: 'offline', detail: 'интерфейс заблокирован' });
}

async function retryIntegrity() {
  const verdict = await verifyUiIntegrity();
  if (!verdict.ok) {
    shell.setLocked(true, { reason: verdict.reason, code: verdict.code });
    return;
  }
  locked = false;
  shell.setLocked(false);
  installWatch();
  await start();
}

// ---------------------------------------------------------------------
// Запуск
// ---------------------------------------------------------------------
async function start() {
  if (locked) return;
  shell.setPanelState({ visible: true, title: 'Загрузка профилей…', hint: 'Запрашиваем список профилей у шлюза', retry: false });

  try {
    const payload = await api.listProfiles();
    const profiles = payload?.profiles ?? [];
    if (!profiles.length) {
      throw new Error('На шлюзе нет профилей — добавьте JSON-файл в каталог profiles/');
    }

    store.set({ profiles });
    shell.setProfiles(profiles, null);

    // Что показать при старте: явный ?profile=, затем борт, который уже
    // выбран на шлюзе (если шлюз его определил), затем сохранённый/первый.
    let requested = resolveProfileId(profiles);
    if (!params.get('profile')) {
      try {
        const state = await api.telemetry();
        const serverProfile = state?.sim?.profileId;
        if (serverProfile && profiles.some((profile) => profile.id === serverProfile)) {
          requested = serverProfile;
        }
      } catch {
        /* шлюз ответит позже — останется сохранённый профиль */
      }
    }

    await selectProfile(requested, false);

    // Явный выбор в ссылке (?profile=…) — это намерение пользователя:
    // сообщаем его шлюзу, иначе mock/SimConnect могут остаться на своём борте.
    const requestedFromUrl = params.get('profile');
    if (requestedFromUrl && profiles.some((profile) => profile.id === requestedFromUrl)) {
      api.selectAircraft(requestedFromUrl).catch((error) => {
        console.warn('selectAircraft failed', error);
      });
    }

    connectSocket();
    started = true;
  } catch (error) {
    shell.setPanelState({
      visible: true,
      title: 'Не удалось загрузить панель',
      hint: error?.message ?? 'Неизвестная ошибка',
      retry: true,
    });
    shell.setConnection({ state: 'offline', detail: 'шлюз недоступен' });
  }
}

async function boot() {
  setupMode();
  setDevice(resolveDeviceId(), false);

  await donation.load();

  const verdict = await verifyUiIntegrity();
  if (!verdict.ok) {
    lockUi(verdict.reason, verdict.code);
    return;
  }

  installWatch();
  await start();
}

window.addEventListener('beforeunload', () => socket?.stop());

boot().catch((error) => {
  console.error(error);
  shell.setPanelState({ visible: true, title: 'Ошибка запуска клиента', hint: String(error?.message ?? error), retry: true });
});

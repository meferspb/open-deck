/**
 * Страница «Сборка Android APK»: настройки, запуск сборки, журнал.
 *
 * Всё общение — с локальным шлюзом (/api/android/*). Никаких внешних
 * сервисов: сборка идёт на этом же компьютере.
 */

import { hydrateDonationLinks } from './core/donation-links.js';
import { initI18n, onLocaleChange, t } from './core/i18n.js';

initI18n();

const FIELDS = [
  'appName',
  'applicationId',
  'versionName',
  'versionCode',
  'defaultHost',
  'defaultPort',
  'jdkPath',
  'sdkPath',
  'gradlePath',
  'timeoutSec',
];

const $ = (id) => document.getElementById(id);
const statusEl = $('android-status');
const logEl = $('android-log');
const toolchainEl = $('android-toolchain');
const downloadEl = $('android-download');

let pollTimer = null;
/** @type {{key: string, params?: Record<string, unknown>, tone?: string} | null} */
let lastStatus = null;
/** @type {any} */
let lastToolchain = null;

function toast(message, tone = 'info') {
  const el = $('toast');
  el.textContent = message;
  el.dataset.tone = tone;
  el.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    el.hidden = true;
  }, 3600);
}

function formValues() {
  const values = {};
  for (const key of FIELDS) {
    const input = $(key);
    if (!input) continue;
    if (input.type === 'number') {
      values[key] = Number(input.value);
    } else {
      values[key] = input.value.trim();
    }
  }
  return values;
}

function fillForm(settings) {
  for (const key of FIELDS) {
    const input = $(key);
    if (input && settings[key] !== undefined && settings[key] !== null) {
      input.value = String(settings[key]);
    }
  }
}

function setStatusKey(key, params = {}, tone = '') {
  lastStatus = { key, params, tone };
  statusEl.textContent = t(key, params);
  statusEl.dataset.tone = tone;
}

function renderToolchain(toolchain) {
  lastToolchain = toolchain;
  if (toolchain?.ok) {
    toolchainEl.textContent = t('android.toolchainFound', {
      jdk: toolchain.jdk,
      sdk: toolchain.sdk,
      gradle: toolchain.gradle,
    });
    toolchainEl.dataset.tone = 'ok';
  } else {
    toolchainEl.textContent = t('android.toolchainMissing', {
      error: toolchain?.error ?? t('android.unknown'),
    });
    toolchainEl.dataset.tone = 'warn';
  }
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
    ...options,
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (!response.ok) {
    throw new Error(data?.error ?? `HTTP ${response.status}`);
  }
  return data;
}

async function loadSettings() {
  setStatusKey('android.loading');
  try {
    const payload = await request('/api/android/settings');
    fillForm(payload.settings ?? {});
    renderToolchain(payload.toolchain);
    setStatusKey('android.settingsLoaded', {}, 'ok');
    if (payload.apk) downloadEl.dataset.ready = 'true';
  } catch (error) {
    setStatusKey('android.settingsLoadFailed', { message: error.message }, 'danger');
  }
}

async function saveSettings() {
  setStatusKey('android.saving');
  try {
    const payload = await request('/api/android/settings', {
      method: 'PUT',
      body: JSON.stringify(formValues()),
    });
    fillForm(payload.settings ?? {});
    renderToolchain(payload.toolchain);
    setStatusKey('android.saved', {}, 'ok');
    toast(t('android.savedToast'));
  } catch (error) {
    setStatusKey('android.settingsError', { message: error.message }, 'danger');
  }
}

function renderJob(job) {
  if (Array.isArray(job.log) && job.log.length) {
    logEl.textContent = job.log.join('\n');
    logEl.scrollTop = logEl.scrollHeight;
  }
  if (job.state === 'running') {
    setStatusKey('android.buildRunning', {}, 'busy');
  } else if (job.state === 'success') {
    setStatusKey('android.buildSuccess', {}, 'ok');
    downloadEl.dataset.ready = 'true';
  } else if (job.state === 'failed') {
    setStatusKey('android.buildFailed', { error: job.error ?? t('android.seeLog') }, 'danger');
  }
}

async function pollBuild() {
  try {
    const job = await request('/api/android/build');
    renderJob(job);
    if (job.running) {
      pollTimer = setTimeout(pollBuild, 1000);
    }
  } catch (error) {
    setStatusKey('android.statusFailed', { message: error.message }, 'danger');
  }
}

async function startBuild() {
  setStatusKey('android.buildStarting');
  logEl.textContent = '';
  try {
    const job = await request('/api/android/build', { method: 'POST', body: '{}' });
    renderJob(job);
    clearTimeout(pollTimer);
    pollTimer = setTimeout(pollBuild, 800);
  } catch (error) {
    setStatusKey('android.buildNotStarted', { message: error.message }, 'danger');
  }
}

for (const id of FIELDS) {
  $(id)?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      saveSettings();
    }
  });
}

$('android-save').addEventListener('click', saveSettings);
$('android-build').addEventListener('click', startBuild);
$('android-download').addEventListener('click', (event) => {
  if (!downloadEl.dataset.ready) {
    event.preventDefault();
    toast(t('android.buildFirst'), 'info');
  }
});

onLocaleChange(() => {
  if (lastToolchain) renderToolchain(lastToolchain);
  if (lastStatus) setStatusKey(lastStatus.key, lastStatus.params, lastStatus.tone);
});

hydrateDonationLinks();
loadSettings().then(() => pollBuild());

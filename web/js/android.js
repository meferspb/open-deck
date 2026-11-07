/**
 * Страница «Сборка Android APK»: настройки, запуск сборки, журнал.
 *
 * Всё общение — с локальным шлюзом (/api/android/*). Никаких внешних
 * сервисов: сборка идёт на этом же компьютере.
 */

import { hydrateDonationLinks } from './core/donation-links.js';

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

function setStatus(text, tone = '') {
  statusEl.textContent = text;
  statusEl.dataset.tone = tone;
}

function renderToolchain(toolchain) {
  if (toolchain?.ok) {
    toolchainEl.textContent = `Инструменты найдены: JDK ${toolchain.jdk} · SDK ${toolchain.sdk} · Gradle ${toolchain.gradle}`;
    toolchainEl.dataset.tone = 'ok';
  } else {
    toolchainEl.textContent = `Инструменты не найдены: ${toolchain?.error ?? 'неизвестно'}`;
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
  setStatus('Загрузка настроек…');
  try {
    const payload = await request('/api/android/settings');
    fillForm(payload.settings ?? {});
    renderToolchain(payload.toolchain);
    setStatus('Настройки загружены. Можно собирать.', 'ok');
    if (payload.apk) downloadEl.dataset.ready = 'true';
  } catch (error) {
    setStatus(`Не удалось загрузить настройки: ${error.message}`, 'danger');
  }
}

async function saveSettings() {
  setStatus('Сохраняем…');
  try {
    const payload = await request('/api/android/settings', {
      method: 'PUT',
      body: JSON.stringify(formValues()),
    });
    fillForm(payload.settings ?? {});
    renderToolchain(payload.toolchain);
    setStatus('Настройки сохранены.', 'ok');
    toast('Настройки APK сохранены');
  } catch (error) {
    setStatus(`Ошибка настроек: ${error.message}`, 'danger');
  }
}

function renderJob(job) {
  if (Array.isArray(job.log) && job.log.length) {
    logEl.textContent = job.log.join('\n');
    logEl.scrollTop = logEl.scrollHeight;
  }
  if (job.state === 'running') {
    setStatus('Сборка идёт… Это может занять до нескольких минут.', 'busy');
  } else if (job.state === 'success') {
    setStatus('Сборка завершена. APK можно скачать.', 'ok');
    downloadEl.dataset.ready = 'true';
  } else if (job.state === 'failed') {
    setStatus(`Сборка не удалась: ${job.error ?? 'см. журнал'}`, 'danger');
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
    setStatus(`Не удалось получить статус: ${error.message}`, 'danger');
  }
}

async function startBuild() {
  setStatus('Запускаем сборку…');
  logEl.textContent = '';
  try {
    const job = await request('/api/android/build', { method: 'POST', body: '{}' });
    renderJob(job);
    clearTimeout(pollTimer);
    pollTimer = setTimeout(pollBuild, 800);
  } catch (error) {
    setStatus(`Сборка не запущена: ${error.message}`, 'danger');
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
    toast('Сначала соберите APK или проверьте готовую сборку', 'info');
  }
});

hydrateDonationLinks();
loadSettings().then(() => pollBuild());

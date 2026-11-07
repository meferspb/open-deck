/**
 * Визуальный редактор приборных панелей (Open Deck Designer).
 *
 * Позволяет в браузере: выбирать профиль, перетаскивать приборы, менять их
 * размер, настраивать привязки/опции и сохранять обратно на хост (PUT).
 * Переопределения под конкретный форм-фактор (layout.phone/…) правятся в
 * активном форм-факторе; если переопределения нет — правка идёт в base.
 */

import { api } from './core/api.js';
import { clamp, normalizeRect, rectFor, snapToGrid } from './core/layout.js';
import { DEVICE_PRESETS, DEVICE_ORDER } from './ui/device.js';
import { createDonation } from './ui/donation.js';
import { verifyUiIntegrity, watchIntegrity } from './ui/integrity.js';
import { createWidgetInstance } from './widgets/registry.js';

// ---------------------------------------------------------------------
// Конфигурация типов приборов: подпись, привязки по умолчанию, команда.
// ---------------------------------------------------------------------
const WIDGET_META = {
  attitude: {
    label: 'Авиагоризонт',
    size: { w: 0.34, h: 0.44 },
    bindings: { pitch: 'attitude.pitchDeg', bank: 'attitude.bankDeg' },
  },
  'gauge.radial': {
    label: 'Круговая шкала',
    size: { w: 0.2, h: 0.3 },
    bindings: { value: 'engine.rpm' },
    options: { min: 0, max: 3500, unit: 'RPM', decimals: 0, majorTicks: 7, minorTicks: 4 },
  },
  readout: {
    label: 'Цифровое табло',
    size: { w: 0.2, h: 0.14 },
    bindings: { value: 'speed.iasKt' },
    options: { unit: 'KT', decimals: 0 },
  },
  'switch.toggle': {
    label: 'Тумблер',
    size: { w: 0.2, h: 0.16 },
    bindings: { state: 'power.batteryMaster' },
    command: { key: 'power.batteryMaster', action: 'set' },
    options: { onLabel: 'ON', offLabel: 'OFF' },
  },
  'knob.rotary': {
    label: 'Галетник',
    size: { w: 0.16, h: 0.2 },
    bindings: { value: 'autopilot.headingBugDeg' },
    command: { key: 'autopilot.headingBugDeg', action: 'set' },
    options: { min: 0, max: 359, step: 1, wrap: true, unit: '°', decimals: 0 },
  },
  annunciator: {
    label: 'Табло-лампа',
    size: { w: 0.24, h: 0.1 },
    bindings: { active: 'power.batteryMaster' },
    options: { tone: 'danger' },
  },
  vsi: {
    label: 'Вариометр',
    size: { w: 0.24, h: 0.32 },
    bindings: { value: 'verticalSpeed.fpm' },
    options: { limit: 2000 },
  },
  altimeter: {
    label: 'Высотомер',
    size: { w: 0.26, h: 0.34 },
    bindings: { value: 'altitude.indicatedFt' },
  },
  heading: {
    label: 'Курсоуказатель',
    size: { w: 0.28, h: 0.34 },
    bindings: { heading: 'heading.magneticDeg', bug: 'autopilot.headingBugDeg' },
  },
};

// Какая переменная (по kind) подходит роли привязки.
const ROLE_KINDS = {
  pitch: 'number',
  bank: 'number',
  value: 'number',
  state: 'bool',
  active: 'bool',
  heading: 'number',
  bug: 'number',
};

// Демо-значения для предпросмотра приборов (без подключения к симулятору).
const DEMO_VALUES = {
  'attitude.pitchDeg': 3.2,
  'attitude.bankDeg': -8.5,
  'engine.rpm': 2350,
  'fuel.totalGal': 31.4,
  'speed.iasKt': 110,
  'altitude.indicatedFt': 4520,
  'verticalSpeed.fpm': 420,
  'heading.magneticDeg': 274,
  'autopilot.headingBugDeg': 290,
  'power.busVolts': 24.2,
  'power.batteryMaster': true,
  'power.avionicsMaster': true,
  'flaps.percent': 15,
  'autopilot.headingBugDeg': 290,
};

const stubState = { values: DEMO_VALUES };
const stubCtx = {
  getState: () => stubState,
  command: () => Promise.resolve({ ok: true }),
  notify: () => {},
};

// ---------------------------------------------------------------------
// Состояние редактора
// ---------------------------------------------------------------------
let profile = null;
let variables = [];
let baseVariables = [];
let deviceClass = 'tablet-lg';
let selectedId = null;
let dirty = false;
/** @type {Map<string, {def: any, wrapper: HTMLElement, instance: any}>} */
const widgets = new Map();
let drag = null;

// История правок: снимки widgets до изменения. Достаточно для отмены
// перемещений, размеров, свойств, добавления и удаления приборов.
const history = { undo: [], redo: [], limit: 80 };

const $ = (id) => document.getElementById(id);

const refs = {
  profileSelect: $('ed-profile'),
  deviceSwitch: $('ed-device'),
  frame: $('ed-frame'),
  screen: $('ed-screen'),
  panel: $('ed-panel'),
  stage: $('ed-stage'),
  props: $('ed-props'),
  deleteBtn: $('ed-delete'),
  addBtn: $('ed-add'),
  saveBtn: $('ed-save'),
  undoBtn: $('ed-undo'),
  redoBtn: $('ed-redo'),
  snap: $('ed-snap'),
  toast: $('ed-toast'),
  hint: $('ed-hint'),
};

// Блок поддержки автора обязателен и здесь: редактор — часть интерфейса хоста.
const donation = createDonation({
  chip: $('donation-badge'),
  dialog: /** @type {HTMLDialogElement} */ ($('donation-dialog')),
  body: $('donation-body'),
  closeButton: $('donation-close'),
});

let toastTimer = null;
function toast(message, tone = 'info') {
  refs.toast.textContent = message;
  refs.toast.dataset.tone = tone;
  refs.toast.hidden = false;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    refs.toast.hidden = true;
  }, 3200);
}

// ---------------------------------------------------------------------
// Устройство (форм-фактор) и рамка
// ---------------------------------------------------------------------
function applyDevice() {
  const preset = DEVICE_PRESETS[deviceClass];
  refs.frame.dataset.device = deviceClass;
  refs.screen.style.width = `${preset.width}px`;
  refs.screen.style.height = `${preset.height}px`;
  refs.frame.style.width = `${preset.width + preset.bezel * 2}px`;
  refs.frame.style.height = `${preset.height + preset.bezel * 2}px`;
  fit();

  for (const button of refs.deviceSwitch.querySelectorAll('[data-device]')) {
    button.setAttribute('aria-pressed', String(button.dataset.device === deviceClass));
  }
  // Раскладка меняется с форм-фактором — перерисовываем позиции.
  refreshLayout();
}

function fit() {
  const availW = Math.max(160, refs.stage.clientWidth - 32);
  const availH = Math.max(160, refs.stage.clientHeight - 32);
  const fw = refs.frame.offsetWidth || 1;
  const fh = refs.frame.offsetHeight || 1;
  const scale = Math.min(1, availW / fw, availH / fh);
  refs.frame.style.transform = `scale(${Math.max(0.2, Number(scale.toFixed(4)))})`;
}

// ---------------------------------------------------------------------
// Загрузка
// ---------------------------------------------------------------------
/** Блокировка редактора при нарушении целостности (условие лицензии). */
function lockEditor(reason, code) {
  document.querySelector('.ed-main')?.remove();
  const overlay = document.createElement('div');
  overlay.className = 'lock-screen';
  const card = document.createElement('div');
  card.className = 'lock-screen__card';
  const eyebrow = document.createElement('p');
  eyebrow.className = 'lock-screen__eyebrow';
  eyebrow.textContent = 'Ошибка целостности';
  const title = document.createElement('h2');
  title.className = 'lock-screen__title';
  title.textContent = 'Работа приложения заблокирована';
  const detail = document.createElement('p');
  detail.className = 'lock-screen__detail';
  detail.textContent = reason || 'Проверка целостности интерфейса не пройдена.';
  const codeEl = document.createElement('code');
  codeEl.className = 'lock-screen__code';
  codeEl.textContent = code ? `код: ${code}` : '';
  card.append(eyebrow, title, detail, codeEl);
  overlay.append(card);
  document.body.append(overlay);
}

async function boot() {
  try {
    await donation.load();

    const verdict = await verifyUiIntegrity();
    if (!verdict.ok) {
      lockEditor(verdict.reason, verdict.code);
      return;
    }
    watchIntegrity({
      badge: document.getElementById('donation-badge'),
      onViolation: (reason, code) => lockEditor(reason, code),
    });

    const [profilesPayload, varsPayload] = await Promise.all([
      api.listProfiles(),
      api.telemetryVariables(),
    ]);
    baseVariables = Array.isArray(varsPayload.variables) ? varsPayload.variables : [];
    variables = baseVariables;

    const profiles = profilesPayload?.profiles ?? [];
    if (!profiles.length) throw new Error('На хосте нет профилей');

    refs.profileSelect.replaceChildren(
      ...profiles.map((p) => {
        const option = document.createElement('option');
        option.value = p.id;
        option.textContent = p.name;
        return option;
      }),
    );
    await loadProfile(profiles[0].id);
  } catch (error) {
    toast(`Не удалось загрузить: ${error.message}`, 'danger');
  }
}

async function loadProfile(id) {
  if (profile && dirty && id !== profile.id) {
    const proceed = window.confirm(
      'В текущем профиле есть несохранённые изменения. Переключиться и потерять их?',
    );
    if (!proceed) {
      refs.profileSelect.value = profile.id;
      return;
    }
  }
  profile = await api.getProfile(id);
  // История принадлежит конкретному профилю: без очистки Ctrl+Z после
  // переключения восстановил бы виджеты предыдущего профиля.
  history.undo.length = 0;
  history.redo.length = 0;
  updateHistoryButtons();
  refs.profileSelect.value = profile.id;
  // В списки привязок попадают и пользовательские переменные профиля (LVAR/RPN).
  const custom = (profile.variables ?? [])
    .filter((item) => item && typeof item.key === 'string')
    .map((item) => ({
      key: item.key,
      label: item.label || item.key,
      kind: item.kind || 'number',
      unit: item.unit || '',
      writable: false,
    }));
  variables = [
    ...baseVariables,
    ...custom.filter((item) => !baseVariables.some((base) => base.key === item.key)),
  ];
  selectedId = null;
  dirty = false;
  refs.saveBtn.textContent = 'Сохранить';
  renderPanel();
  renderProperties();
}

// ---------------------------------------------------------------------
// Рендер панели
// ---------------------------------------------------------------------
function renderPanel() {
  for (const { instance } of widgets.values()) {
    try {
      instance.destroy();
    } catch {
      /* игнорируем */
    }
  }
  widgets.clear();
  refs.panel.replaceChildren();
  refs.panel.style.setProperty('--panel-bg', profile?.panel?.background ?? '#0b1117');

  for (const def of profile?.widgets ?? []) {
    createWidgetElement(def);
  }

  if (profile?.panel?.footer) {
    const footer = document.createElement('div');
    footer.className = 'panel__footer';
    footer.textContent = profile.panel.footer;
    refs.panel.append(footer);
  }

  applyDevice();
  refreshLayout();
}

function createWidgetElement(def) {
  const wrapper = document.createElement('div');
  wrapper.className = 'ed-widget';
  wrapper.dataset.id = def.id;
  wrapper.setAttribute('role', 'button');
  wrapper.setAttribute('aria-label', `Прибор ${def.label ?? def.id}`);

  const preview = document.createElement('div');
  preview.className = 'ed-widget__preview';
  const frame = document.createElement('div');
  frame.className = 'ed-widget__frame';
  const idLabel = document.createElement('div');
  idLabel.className = 'ed-widget__id';
  idLabel.textContent = def.id;
  const handle = document.createElement('div');
  handle.className = 'ed-widget__handle';
  handle.title = 'Изменить размер';

  wrapper.append(preview, frame, idLabel, handle);
  refs.panel.append(wrapper);

  const instance = createWidgetInstance(def, preview, stubCtx);
  try {
    instance.mount();
    instance.update(stubState, 0);
  } catch {
    /* прибор-заглушка или ошибка рендера — не критично */
  }

  widgets.set(def.id, { def, wrapper, instance });

  wrapper.addEventListener('pointerdown', (event) => onPointerDown(event, def.id));
  handle.addEventListener('pointerdown', (event) => {
    event.stopPropagation();
    onPointerDown(event, def.id, 'resize');
  });
}

function refreshLayout() {
  const width = refs.screen.clientWidth;
  const height = refs.screen.clientHeight;
  for (const { def, wrapper, instance } of widgets.values()) {
    const rect = rectFor(def, deviceClass);
    wrapper.style.left = `${rect.x * 100}%`;
    wrapper.style.top = `${rect.y * 100}%`;
    wrapper.style.width = `${rect.w * 100}%`;
    wrapper.style.height = `${rect.h * 100}%`;
    wrapper.style.setProperty('--w', `${Math.round(rect.w * width)}px`);
    wrapper.style.setProperty('--h', `${Math.round(rect.h * height)}px`);
    try {
      instance.update(stubState, 0);
    } catch {
      /* игнорируем */
    }
  }
  setSelected(selectedId);
}

function setSelected(id) {
  selectedId = id;
  for (const [wid, { wrapper }] of widgets) {
    wrapper.classList.toggle('is-selected', wid === id);
  }
  refs.deleteBtn.hidden = !id;
  renderProperties();
}

// ---------------------------------------------------------------------
// Drag / resize
// ---------------------------------------------------------------------
/** @returns {{x:number,y:number,w:number,h:number}} редактируемый прямоугольник */
function editableRect(widget) {
  const layout = widget.layout ?? (widget.layout = {});
  if (layout[deviceClass] && typeof layout[deviceClass] === 'object') {
    return layout[deviceClass];
  }
  if (!layout.base) layout.base = { x: 0.05, y: 0.05, w: 0.2, h: 0.2 };
  return layout.base;
}

function onPointerDown(event, id, mode = 'move') {
  setSelected(id);
  const widget = profile.widgets.find((w) => w.id === id);
  if (!widget) return;

  const startRect = normalizeRect(rectFor(widget, deviceClass));
  // Превью масштабируется transform: scale(), поэтому пересчёт долей должен
  // идти по отображаемым размерам, иначе прибор «убегает» от курсора.
  const screenRect = refs.screen.getBoundingClientRect();
  drag = {
    id,
    mode,
    startX: event.clientX,
    startY: event.clientY,
    rect: startRect,
    panelW: screenRect.width || refs.screen.clientWidth,
    panelH: screenRect.height || refs.screen.clientHeight,
    historyPushed: false,
  };
  const wrapper = widgets.get(id)?.wrapper;
  wrapper?.classList.add('is-dragging');
  try {
    wrapper?.setPointerCapture?.(event.pointerId);
  } catch {
    // Синтетические события и потерянный захват не должны ломать перетаскивание.
  }
  event.preventDefault();
}

function onPointerMove(event) {
  if (!drag) return;
  if (!drag.historyPushed) {
    // Снимок до первого фактического изменения — один шаг отмены на перетаскивание.
    pushHistory();
    drag.historyPushed = true;
  }

  const dx = (event.clientX - drag.startX) / (drag.panelW || 1);
  const dy = (event.clientY - drag.startY) / (drag.panelH || 1);
  const widget = profile.widgets.find((w) => w.id === drag.id);
  if (!widget) return;

  const snapStep = refs.snap?.checked && !event.shiftKey ? 0.01 : 0;
  const snap = (value) => (snapStep > 0 ? round4(snapToGrid(value, snapStep)) : value);

  const target = editableRect(widget);
  const { x, y, w, h } = drag.rect;

  if (drag.mode === 'move') {
    target.x = round4(clamp(snap(x + dx), 0, 1 - w));
    target.y = round4(clamp(snap(y + dy), 0, 1 - h));
  } else {
    target.w = round4(clamp(snap(w + dx), 0.02, 1 - x));
    target.h = round4(clamp(snap(h + dy), 0.02, 1 - y));
  }

  applyWidgetLayout(widgets.get(drag.id));
  dirty = true;
}

function onPointerUp() {
  if (!drag) return;
  const wrapper = widgets.get(drag.id)?.wrapper;
  wrapper?.classList.remove('is-dragging');
  drag = null;
  markDirty();
}

function applyWidgetLayout(entry) {
  if (!entry) return;
  const { def, wrapper } = entry;
  const rect = rectFor(def, deviceClass);
  wrapper.style.left = `${rect.x * 100}%`;
  wrapper.style.top = `${rect.y * 100}%`;
  wrapper.style.width = `${rect.w * 100}%`;
  wrapper.style.height = `${rect.h * 100}%`;
  wrapper.style.setProperty('--w', `${Math.round(rect.w * refs.screen.clientWidth)}px`);
  wrapper.style.setProperty('--h', `${Math.round(rect.h * refs.screen.clientHeight)}px`);
}

const round4 = (value) => Math.round(value * 10000) / 10000;

document.addEventListener('pointermove', onPointerMove);
document.addEventListener('pointerup', onPointerUp);
document.addEventListener('pointercancel', onPointerUp);

// ---------------------------------------------------------------------
// Панель свойств
// ---------------------------------------------------------------------
function variablesForRole(role) {
  const kind = ROLE_KINDS[role];
  return variables.filter((v) => !kind || v.kind === kind);
}

function makeField(labelText, inputEl) {
  const field = document.createElement('label');
  field.className = 'ed-field';
  const label = document.createElement('span');
  label.className = 'ed-field__label';
  label.textContent = labelText;
  field.append(label, inputEl);
  return field;
}

function textInput(value, onChange) {
  const input = document.createElement('input');
  input.className = 'ed-input';
  input.type = 'text';
  input.value = value ?? '';
  let touched = false;
  input.addEventListener('focus', () => {
    touched = false;
  });
  input.addEventListener('input', () => {
    if (!touched) {
      pushHistory();
      touched = true;
    }
    onChange(input.value);
  });
  return input;
}

function numberInput(value, onChange, step = 0.01) {
  const input = document.createElement('input');
  input.className = 'ed-input';
  input.type = 'number';
  input.step = String(step);
  input.value = value ?? '';
  let touched = false;
  input.addEventListener('focus', () => {
    touched = false;
  });
  input.addEventListener('input', () => {
    if (!touched) {
      pushHistory();
      touched = true;
    }
    onChange(Number(input.value));
  });
  return input;
}

function selectInput(options, value, onChange) {
  const select = document.createElement('select');
  select.className = 'ed-select';
  for (const option of options) {
    const el = document.createElement('option');
    el.value = option.value;
    el.textContent = option.label;
    select.append(el);
  }
  select.value = value ?? '';
  select.addEventListener('change', () => {
    pushHistory();
    onChange(select.value);
  });
  return select;
}

function section(title) {
  const el = document.createElement('div');
  el.className = 'ed-section';
  el.textContent = title;
  return el;
}

function renderProperties() {
  refs.props.replaceChildren();
  const def = profile?.widgets.find((w) => w.id === selectedId);
  if (!def) {
    refs.props.append(
      Object.assign(document.createElement('p'), {
        className: 'ed-empty',
        textContent:
          'Выберите прибор на панели, чтобы изменить его свойства.\n\n' +
          'Перетаскивание — сдвинуть, угол — изменить размер. ' +
          'Переопределения под форм-фактор правятся в активном форм-факторе.',
      }),
    );
    return;
  }

  const update = (patch) => {
    Object.assign(def, patch);
    dirty = true;
    markDirty();
    refreshWidget(def);
  };

  refs.props.append(
    makeField(
      'ID',
      textInput(def.id, (v) => {
        const slug = v.trim().toLowerCase().replace(/[^a-z0-9-]+/g, '-').replace(/^-+|-+$/g, '');
        if (slug && !profile.widgets.some((w) => w !== def && w.id === slug)) {
          const old = def.id;
          def.id = slug;
          const entry = widgets.get(old);
          widgets.delete(old);
          widgets.set(slug, entry);
          entry.wrapper.dataset.id = slug;
          entry.wrapper.querySelector('.ed-widget__id').textContent = slug;
          selectedId = slug;
          dirty = true;
          markDirty();
        }
      }),
    ),
    makeField('Подпись (label)', textInput(def.label ?? '', (v) => update({ label: v }))),
  );

  // Привязки.
  if (def.bindings) {
    refs.props.append(section('Привязки'));
    for (const role of Object.keys(def.bindings)) {
      const options = variablesForRole(role).map((v) => ({
        value: v.key,
        label: `${v.label} (${v.key})`,
      }));
      refs.props.append(
        makeField(
          role,
          selectInput(options, def.bindings[role], (v) => {
            def.bindings[role] = v;
            dirty = true;
            markDirty();
            refreshWidget(def);
          }),
        ),
      );
    }
  }

  // Команда.
  if (def.command) {
    refs.props.append(section('Команда'));
    const writable = variables.filter((v) => v.writable).map((v) => ({
      value: v.key,
      label: `${v.label} (${v.key})`,
    }));
    refs.props.append(
      makeField(
        'Переменная записи',
        selectInput(writable, def.command.key, (v) => {
          def.command.key = v;
          dirty = true;
          markDirty();
        }),
      ),
    );
  }

  // Опции (зависит от типа).
  const options = def.options ?? (def.options = {});
  refs.props.append(section('Опции'));
  refs.props.append(makeField('Заголовок (caption)', textInput(options.caption ?? '', (v) => updateOptions('caption', v))));

  if (def.type === 'readout' || def.type === 'gauge.radial' || def.type === 'knob.rotary') {
    refs.props.append(makeField('Единица (unit)', textInput(options.unit ?? '', (v) => updateOptions('unit', v))));
    refs.props.append(
      makeField('Знаков после запятой', numberInput(options.decimals ?? 0, (v) => updateOptions('decimals', v), 1)),
    );
  }
  if (def.type === 'gauge.radial' || def.type === 'knob.rotary') {
    const row = document.createElement('div');
    row.className = 'ed-row';
    row.append(
      makeField('Минимум', numberInput(options.min ?? 0, (v) => updateOptions('min', v), 1)),
      makeField('Максимум', numberInput(options.max ?? 100, (v) => updateOptions('max', v), 1)),
    );
    refs.props.append(row);
  }
  if (def.type === 'switch.toggle') {
    const row = document.createElement('div');
    row.className = 'ed-row';
    row.append(
      makeField('ON', textInput(options.onLabel ?? 'ON', (v) => updateOptions('onLabel', v))),
      makeField('OFF', textInput(options.offLabel ?? 'OFF', (v) => updateOptions('offLabel', v))),
    );
    refs.props.append(row);
  }
  if (def.type === 'annunciator') {
    refs.props.append(
      makeField(
        'Тон',
        selectInput(
          [
            { value: 'danger', label: 'danger (красный)' },
            { value: 'warn', label: 'warn (янтарный)' },
            { value: 'ok', label: 'ok (зелёный)' },
          ],
          options.tone ?? 'danger',
          (v) => updateOptions('tone', v),
        ),
      ),
    );
  }

  // Точная геометрия активного форм-фактора.
  refs.props.append(section(`Геометрия · ${deviceClass}`));
  const rect = editableRect(def);
  const geo = document.createElement('div');
  geo.className = 'ed-row';
  const setGeo = (key, v) => {
    if (Number.isFinite(v)) {
      // Ширина/высота не могут схлопнуться в ноль: прибор обязан остаться видимым.
      rect[key] = round4(clamp(v, key === 'w' || key === 'h' ? 0.02 : 0, 1));
      dirty = true;
      markDirty();
      applyWidgetLayout(widgets.get(def.id));
    }
  };
  geo.append(
    makeField('X', numberInput(rect.x, (v) => setGeo('x', v))),
    makeField('Y', numberInput(rect.y, (v) => setGeo('y', v))),
    makeField('W', numberInput(rect.w, (v) => setGeo('w', v))),
    makeField('H', numberInput(rect.h, (v) => setGeo('h', v))),
  );
  refs.props.append(geo);

  // Копирование геометрии в другие форм-факторы одним нажатием.
  refs.props.append(section('Раскладка форм-факторов'));
  const copyRow = document.createElement('div');
  copyRow.className = 'ed-row';
  for (const factor of DEVICE_ORDER) {
    if (factor === deviceClass) continue;
    const preset = DEVICE_PRESETS[factor];
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ed-btn ed-btn--ghost';
    button.textContent = `→ ${preset?.title ?? factor}`;
    button.title = `Скопировать текущую геометрию в «${preset?.title ?? factor}»`;
    button.addEventListener('click', () => {
      if (!profile) return;
      pushHistory();
      const layout = def.layout ?? (def.layout = {});
      layout[factor] = { ...editableRect(def) };
      dirty = true;
      markDirty();
      toast(`Геометрия скопирована: ${preset?.title ?? factor}`);
    });
    copyRow.append(button);
  }
  refs.props.append(copyRow);
}

function updateOptions(key, value) {
  const def = profile.widgets.find((w) => w.id === selectedId);
  if (!def) return;
  const options = def.options ?? (def.options = {});
  options[key] = value === '' ? undefined : value;
  dirty = true;
  markDirty();
  refreshWidget(def);
}

function refreshWidget(def) {
  const entry = widgets.get(def.id);
  if (!entry) return;
  applyWidgetLayout(entry);
  try {
    entry.instance.update(stubState, 0);
  } catch {
    /* игнорируем */
  }
}

function markDirty() {
  refs.saveBtn.textContent = dirty ? 'Сохранить ●' : 'Сохранить';
}

// ---------------------------------------------------------------------
// История правок (undo/redo)
// ---------------------------------------------------------------------
function snapshotWidgets() {
  return JSON.stringify(profile?.widgets ?? []);
}

function updateHistoryButtons() {
  if (refs.undoBtn) refs.undoBtn.disabled = history.undo.length === 0;
  if (refs.redoBtn) refs.redoBtn.disabled = history.redo.length === 0;
}

function pushHistory() {
  if (!profile) return;
  history.undo.push(snapshotWidgets());
  if (history.undo.length > history.limit) history.undo.shift();
  history.redo.length = 0;
  updateHistoryButtons();
}

function restoreWidgets(json) {
  if (!profile) return;
  try {
    profile.widgets = JSON.parse(json);
  } catch {
    return;
  }
  selectedId = null;
  drag = null;
  renderPanel();
  renderProperties();
  dirty = true;
  markDirty();
  updateHistoryButtons();
}

function undo() {
  if (!profile || history.undo.length === 0) return;
  history.redo.push(snapshotWidgets());
  restoreWidgets(history.undo.pop());
  toast('Действие отменено');
}

function redo() {
  if (!profile || history.redo.length === 0) return;
  history.undo.push(snapshotWidgets());
  restoreWidgets(history.redo.pop());
  toast('Действие повторено');
}

// ---------------------------------------------------------------------
// Добавить / удалить / сохранить
// ---------------------------------------------------------------------
function showPalette() {
  const overlay = document.createElement('div');
  overlay.style.cssText =
    'position:fixed;inset:0;z-index:40;display:grid;place-items:center;background:rgba(3,5,8,.72);backdrop-filter:blur(3px);';
  const card = document.createElement('div');
  card.style.cssText =
    'width:min(360px,92vw);max-height:76vh;overflow:auto;padding:18px;border-radius:18px;border:1px solid var(--line-strong);background:#0b1117;box-shadow:var(--shadow-panel);';
  const title = document.createElement('h2');
  title.textContent = 'Добавить прибор';
  title.style.cssText = 'margin:0 0 12px;font-size:16px;';
  card.append(title);

  const palette = document.createElement('div');
  palette.className = 'ed-palette';
  for (const [type, meta] of Object.entries(WIDGET_META)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ed-palette__item';
    button.textContent = meta.label;
    button.addEventListener('click', () => {
      addWidget(type);
      overlay.remove();
    });
    palette.append(button);
  }
  card.append(palette);
  overlay.append(card);
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) overlay.remove();
  });
  document.body.append(overlay);
}

function addWidget(type) {
  const meta = WIDGET_META[type];
  if (!meta || !profile) return;
  pushHistory();
  const baseId = `widget-${profile.widgets.length + 1}`;
  let id = baseId;
  let n = 1;
  while (profile.widgets.some((w) => w.id === id)) {
    id = `${baseId}-${++n}`;
  }

  const def = {
    id,
    type,
    label: meta.label,
    bindings: { ...meta.bindings },
    layout: {
      base: { x: 0.06, y: 0.06, w: meta.size?.w ?? 0.2, h: meta.size?.h ?? 0.2 },
    },
    options: { ...(meta.options ?? {}) },
  };
  if (meta.command) def.command = { ...meta.command };

  profile.widgets.push(def);
  createWidgetElement(def);
  refreshLayout();
  setSelected(id);
  dirty = true;
  markDirty();
}

function deleteSelected() {
  if (!selectedId || !profile) return;
  const index = profile.widgets.findIndex((w) => w.id === selectedId);
  if (index < 0) return;
  pushHistory();
  const entry = widgets.get(selectedId);
  try {
    entry?.instance.destroy();
  } catch {
    /* игнорируем */
  }
  entry?.wrapper.remove();
  widgets.delete(selectedId);
  profile.widgets.splice(index, 1);
  selectedId = null;
  dirty = true;
  markDirty();
  setSelected(null);
}

let saving = false;

async function save() {
  if (!profile || saving) return;
  saving = true;
  const previousRevision = profile.revision;
  try {
    // id в URL должен совпадать с id профиля; порядок виджетов сохраняем.
    // Ревизия растёт при каждом сохранении — по ней видно, что файл менялся.
    const revision = Number(profile.revision);
    profile.revision = Number.isFinite(revision) && revision >= 1 ? revision + 1 : 1;
    await api.saveProfile(profile);
    dirty = false;
    markDirty();
    toast('Профиль сохранён на хосте');
  } catch (error) {
    // Сохранение не удалось — откатываем ревизию, чтобы не «съедать» номера.
    profile.revision = previousRevision;
    toast(`Ошибка сохранения: ${error.message}`, 'danger');
  } finally {
    saving = false;
  }
}

// ---------------------------------------------------------------------
// События
// ---------------------------------------------------------------------
refs.profileSelect.addEventListener('change', () => {
  loadProfile(refs.profileSelect.value).catch((error) => {
    if (profile) refs.profileSelect.value = profile.id;
    toast(error.message, 'danger');
  });
});
for (const button of refs.deviceSwitch.querySelectorAll('[data-device]')) {
  button.addEventListener('click', () => {
    deviceClass = button.dataset.device;
    applyDevice();
  });
}
refs.addBtn.addEventListener('click', showPalette);
refs.saveBtn.addEventListener('click', save);
refs.deleteBtn.addEventListener('click', deleteSelected);
refs.undoBtn?.addEventListener('click', undo);
refs.redoBtn?.addEventListener('click', redo);

document.addEventListener('keydown', (event) => {
  const tag = event.target?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  if (!event.ctrlKey && !event.metaKey) return;
  const key = event.key.toLowerCase();
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault();
    undo();
  } else if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault();
    redo();
  }
});

updateHistoryButtons();
window.addEventListener('resize', () => {
  fit();
  refreshLayout();
});
new ResizeObserver(() => {
  fit();
  refreshLayout();
}).observe(refs.stage);

window.addEventListener('beforeunload', (event) => {
  if (dirty) event.preventDefault();
});

boot();

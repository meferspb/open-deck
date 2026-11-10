/**
 * Сцена: рамка устройства и масштабирование под окно.
 *
 * Два режима:
 *  - frame  — превью на большом экране (Windows-хост, планшет в альбомной
 *             ориентации): рисуется «корпус» устройства нужного размера;
 *  - full   — реальный телефон/планшет: панель занимает весь экран.
 */

import { getPreset } from './device.js';

/**
 * @param {{stage: HTMLElement, frame: HTMLElement, screen: HTMLElement, panel: HTMLElement}} elements
 */
export function createStage({ stage, frame, screen, panel }) {
  /** @type {'frame'|'full'} */
  let mode = 'frame';
  let preset = getPreset('tablet-lg');
  let scheduled = 0;

  /** --u = 1% ширины панели: от него считаются все размеры текста. */
  function updateUnit() {
    const width = screen.clientWidth;
    if (width > 0) panel.style.setProperty('--u', `${width / 100}px`);
  }

  function applyPreset() {
    frame.dataset.device = preset.id;
    frame.style.padding = `${preset.bezel}px`;
    frame.style.borderRadius = `${preset.radius}px`;
    screen.style.borderRadius = `${Math.max(2, preset.radius - preset.bezel)}px`;
  }

  function fit() {
    // В полноэкранном режиме панель занимает всю сцену; рамка нужна только
    // для явного превью устройства через `?frame=1`.
    if (mode === 'full') return;
    const frameWidth = frame.offsetWidth;
    const frameHeight = frame.offsetHeight;
    if (!frameWidth || !frameHeight) return;

    const availableWidth = Math.max(120, stage.clientWidth - 24);
    const availableHeight = Math.max(120, stage.clientHeight - 24);
    const scale = Math.min(1, availableWidth / frameWidth, availableHeight / frameHeight);
    frame.style.transform = `scale(${Math.max(0.28, Number(scale.toFixed(4)))})`;
  }

  function applyMode() {
    stage.dataset.mode = mode;
    frame.dataset.mode = mode;

    if (mode === 'full') {
      // Рабочий режим: панель заполняет всю сцену.
      frame.style.position = '';
      frame.style.left = '';
      frame.style.top = '';
      frame.style.width = '100%';
      frame.style.height = '100%';
      frame.style.padding = '0';
      frame.style.borderRadius = '0';
      frame.style.transform = 'none';
      screen.style.width = '100%';
      screen.style.height = '100%';
      screen.style.borderRadius = '0';
    } else {
      frame.style.position = '';
      frame.style.left = '';
      frame.style.top = '';
      applyPreset();
      screen.style.width = `${preset.width}px`;
      screen.style.height = `${preset.height}px`;
      frame.style.width = `${preset.width + preset.bezel * 2}px`;
      frame.style.height = `${preset.height + preset.bezel * 2}px`;
      fit();
    }
    scheduleRefresh();
  }

  function scheduleRefresh() {
    if (scheduled) return;
    scheduled = requestAnimationFrame(() => {
      scheduled = 0;
      fit();
      updateUnit();
    });
  }

  const resizeObserver = new ResizeObserver(scheduleRefresh);
  resizeObserver.observe(stage);
  resizeObserver.observe(screen);

  return {
    /** @param {'frame'|'full'} next */
    setMode(next) {
      mode = next === 'full' ? 'full' : 'frame';
      applyMode();
    },
    /** @param {string} id */
    setPreset(id) {
      preset = getPreset(id);
      applyPreset();
      applyMode();
    },
    get preset() {
      return preset;
    },
    get mode() {
      return mode;
    },
    refresh: scheduleRefresh,
  };
}

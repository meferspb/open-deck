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
    const frameWidth = mode === 'full' ? preset.width : frame.offsetWidth;
    const frameHeight = mode === 'full' ? preset.height : frame.offsetHeight;
    if (!frameWidth || !frameHeight) return;

    const gutter = mode === 'full' ? 0 : 24;
    const availableWidth = Math.max(120, stage.clientWidth - gutter);
    const availableHeight = Math.max(120, stage.clientHeight - gutter);
    const scale = Math.min(
      mode === 'full' ? Number.POSITIVE_INFINITY : 1,
      availableWidth / frameWidth,
      availableHeight / frameHeight,
    );
    const value = Math.max(0.28, Number(scale.toFixed(4)));
    frame.style.transform = mode === 'full'
      ? `translate(-50%, -50%) scale(${value})`
      : `scale(${value})`;
  }

  function applyMode() {
    stage.dataset.mode = mode;
    frame.dataset.mode = mode;

    if (mode === 'full') {
      // Реальный телефон/планшет: сохраняем логический размер профиля и
      // вписываем его в сцену целиком. Иначе короткий viewport сжимает
      // приборы по высоте и их показания обрезаются.
      frame.style.position = 'absolute';
      frame.style.left = '50%';
      frame.style.top = '50%';
      frame.style.width = `${preset.width}px`;
      frame.style.height = `${preset.height}px`;
      frame.style.padding = '0';
      frame.style.borderRadius = '0';
      screen.style.width = `${preset.width}px`;
      screen.style.height = `${preset.height}px`;
      screen.style.borderRadius = '0';
      fit();
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

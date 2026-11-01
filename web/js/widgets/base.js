/**
 * Базовый класс прибора и небольшие утилиты: DOM, HiDPI-canvas, сглаживание.
 * Прибор получает обновления каждый кадр, поэтому анимация не зависит
 * от частоты сети (20 Гц) и остаётся плавной на 60 Гц.
 */

export class Widget {
  /**
   * @param {HTMLElement} element
   * @param {{getState: () => any, command: (key: string, value: unknown) => Promise<any>, notify?: (message: string) => void}} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    this.el = element;
    this.ctx = ctx;
    this.def = def ?? {};
    this.options = this.def.options ?? {};
    this.bindings = this.def.bindings ?? {};
  }

  mount() {}

  /**
   * @param {any} state кадр телеметрии
   * @param {number} now
   */
  update(state, now) {}

  destroy() {}

  /**
   * Значение из привязки по роли (pitch/bank/value/state/active).
   * @param {any} state
   * @param {string} role
   */
  bindingValue(state, role) {
    const key = this.bindings[role];
    if (!key) return undefined;
    return state?.values?.[key];
  }
}

/**
 * @param {string} tag
 * @param {string} [className]
 * @param {string} [text]
 * @returns {HTMLElement}
 */
export function h(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

/**
 * @param {HTMLElement} host
 * @param {string} [modifier]
 */
export function createCard(host, modifier) {
  const card = h('div', modifier ? `card ${modifier}` : 'card');
  host.append(card);
  return card;
}

/**
 * Canvas с учётом devicePixelRatio. Размеры берутся из CSS-пикселей
 * родителя (clientWidth), поэтому масштабирование превью не влияет.
 */
export class CanvasSurface {
  /** @param {HTMLElement} host */
  constructor(host) {
    this.canvas = document.createElement('canvas');
    this.canvas.setAttribute('aria-hidden', 'true');
    host.append(this.canvas);
    this.ctx = /** @type {CanvasRenderingContext2D} */ (this.canvas.getContext('2d'));
    this.width = 0;
    this.height = 0;
    this.dpr = 1;
  }

  /** @returns {boolean} true, если размер изменился */
  resize() {
    const host = this.canvas.parentElement;
    const width = Math.max(1, Math.round(host?.clientWidth ?? 0));
    const height = Math.max(1, Math.round(host?.clientHeight ?? 0));
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (width === this.width && height === this.height && dpr === this.dpr) return false;

    this.width = width;
    this.height = height;
    this.dpr = dpr;
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return true;
  }

  clear() {
    this.ctx.clearRect(0, 0, this.width, this.height);
  }
}

/**
 * Экспоненциальное сглаживание значения — стрелки и авиагоризонт
 * не дёргаются от сетевых пакетов.
 */
export class Smoother {
  /**
   * @param {number} [value]
   * @param {number} [tau] постоянная времени, секунды
   */
  constructor(value = 0, tau = 0.15) {
    this.value = value;
    this.target = value;
    this.tau = tau;
    this.last = 0;
  }

  /**
   * @param {number} target
   * @param {number} now
   */
  update(target, now) {
    if (Number.isFinite(target)) this.target = target;
    const dt = this.last ? Math.min(0.1, Math.max(0, (now - this.last) / 1000)) : 1 / 60;
    this.last = now;
    const k = 1 - Math.exp(-dt / Math.max(this.tau, 1e-3));
    this.value += (this.target - this.value) * k;
    return this.value;
  }

  /** @param {number} value */
  snap(value) {
    this.value = value;
    this.target = value;
    this.last = 0;
  }
}

/** @param {number} degrees */
export function degToRad(degrees) {
  return (degrees * Math.PI) / 180;
}

export const TONE_COLORS = Object.freeze({
  ok: '#38d39f',
  warn: '#ffb020',
  danger: '#ff5d5d',
  accent: '#4cc2ff',
});

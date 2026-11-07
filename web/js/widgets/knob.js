/**
 * Галетник / вращающаяся ручка (gesture control).
 *
 * Управление: перетаскивание вверх-вниз, колесо мыши, стрелки клавиатуры.
 * Команды уходят с троттлингом (не чаще ~12 в секунду): даже длинный
 * свайп не заливает сеть, а последнее значение отправляется сразу.
 */

import { formatNumber, toFiniteNumber } from '../core/format.js';
import { CanvasSurface, Smoother, Widget, createCard, degToRad } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';
const SEND_THROTTLE_MS = 80;

export class KnobWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--knob');

    this.key = this.def.command?.key ?? null;
    this.min = Number(this.options.min ?? 0);
    this.max = Number(this.options.max ?? 359);
    this.wrap = Boolean(this.options.wrap);
    this.step = Number(this.options.step) || 1;
    this.decimals = Number(this.options.decimals ?? 0);
    this.unit = typeof this.options.unit === 'string' ? this.options.unit : '';
    this.caption = this.options.caption ?? def.label ?? 'KNOB';
    this.sensitivity = (this.max - this.min) / 240;

    this.card = createCard(element, 'knob');
    this.card.tabIndex = 0;
    this.card.setAttribute('role', 'slider');
    this.card.setAttribute('aria-valuemin', String(this.min));
    this.card.setAttribute('aria-valuemax', String(this.max));
    this.card.setAttribute('aria-label', this.caption);
    this.surface = new CanvasSurface(this.card);

    this.value = this.min;
    this.display = new Smoother(this.min, 0.08);
    this.hasData = false;
    this.dragging = false;
    this.lastPointerY = 0;
    this.pendingSend = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    this.sendTimer = null;

    this.onPointerDown = this.onPointerDown.bind(this);
    this.onPointerMove = this.onPointerMove.bind(this);
    this.onPointerUp = this.onPointerUp.bind(this);
    this.card.addEventListener('pointerdown', this.onPointerDown);
    this.card.addEventListener('pointermove', this.onPointerMove);
    this.card.addEventListener('pointerup', this.onPointerUp);
    this.card.addEventListener('pointercancel', this.onPointerUp);
    this.card.addEventListener('wheel', (event) => this.onWheel(event), { passive: false });
    this.card.addEventListener('keydown', (event) => this.onKeyDown(event));
  }

  // --- ввод -----------------------------------------------------------
  /** @param {PointerEvent} event */
  onPointerDown(event) {
    if (!this.key) return;
    this.dragging = true;
    this.lastPointerY = event.clientY;
    this.card.setPointerCapture?.(event.pointerId);
    this.card.focus({ preventScroll: true });
    event.preventDefault();
  }

  /** @param {PointerEvent} event */
  onPointerMove(event) {
    if (!this.dragging) return;
    const deltaY = this.lastPointerY - event.clientY;
    this.lastPointerY = event.clientY;
    this.applyValue(this.value + deltaY * this.sensitivity);
  }

  /** @param {PointerEvent} event */
  onPointerUp(event) {
    if (!this.dragging) return;
    this.dragging = false;
    try {
      this.card.releasePointerCapture?.(event.pointerId);
    } catch {
      // Захват уже снят (pointercancel) — это не ошибка.
    }
    this.flushSend();
  }

  /** @param {WheelEvent} event */
  onWheel(event) {
    if (!this.key) return;
    event.preventDefault();
    const direction = event.deltaY < 0 ? 1 : -1;
    this.applyValue(this.value + direction * this.step);
    this.flushSend();
  }

  /** @param {KeyboardEvent} event */
  onKeyDown(event) {
    if (!this.key) return;
    const big = event.shiftKey ? 10 : 1;
    let next = null;
    if (event.key === 'ArrowUp' || event.key === 'ArrowRight') next = this.value + this.step * big;
    if (event.key === 'ArrowDown' || event.key === 'ArrowLeft') next = this.value - this.step * big;
    if (event.key === 'PageUp') next = this.value + this.step * 10;
    if (event.key === 'PageDown') next = this.value - this.step * 10;
    if (next === null) return;
    event.preventDefault();
    this.applyValue(next);
    this.flushSend();
  }

  // --- значение и отправка -------------------------------------------
  /** @param {number} raw */
  clampValue(raw) {
    if (!Number.isFinite(raw)) return this.value;
    if (!this.wrap) return Math.min(this.max, Math.max(this.min, raw));
    const span = this.max - this.min + this.step;
    return this.min + (((raw - this.min) % span) + span) % span;
  }

  /** @param {number} next */
  applyValue(next) {
    this.value = this.clampValue(next);
    this.pendingSend = this.value;
    if (this.sendTimer) return;
    this.sendTimer = setTimeout(() => {
      this.sendTimer = null;
      this.flushSend();
    }, SEND_THROTTLE_MS);
  }

  flushSend() {
    if (this.sendTimer) {
      clearTimeout(this.sendTimer);
      this.sendTimer = null;
    }
    if (this.pendingSend === null || !this.key) return;
    const value = this.pendingSend;
    this.pendingSend = null;

    this.ctx
      .command(this.key, value)
      .catch((error) => {
        this.ctx.notify?.(`${this.caption}: ${error?.message ?? 'команда не выполнена'}`);
      });
  }

  update(state, now = performance.now()) {
    const raw = toFiniteNumber(this.bindingValue(state, 'value'));
    this.hasData = raw !== null;
    if (raw !== null && !this.dragging && this.pendingSend === null) {
      this.value = raw;
    }
    const shown = this.display.update(this.value, now);
    this.card.setAttribute('aria-valuenow', String(Math.round(this.value)));
    this.surface.resize();
    this.draw(shown);
  }

  /** @param {number} shown */
  draw(shown) {
    const { ctx, width: w, height: h } = this.surface;
    ctx.clearRect(0, 0, w, h);
    if (w < 40 || h < 40) return;

    const cx = w / 2;
    const cy = h * 0.5;
    const radius = Math.min(w * 0.3, h * 0.3);

    // Подпись.
    ctx.fillStyle = 'rgba(143, 163, 184, 0.9)';
    ctx.font = `600 ${Math.max(8, Math.round(h * 0.075))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.caption.toUpperCase(), cx, h * 0.09);

    // Шкала.
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.09)';
    ctx.lineWidth = Math.max(3, radius * 0.12);
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.stroke();

    for (let i = 0; i < 72; i += 1) {
      const angle = degToRad(-90 + i * 5);
      const major = i % 9 === 0;
      const inner = radius * (major ? 0.82 : 0.9);
      const outer = radius * 0.99;
      ctx.strokeStyle = major ? 'rgba(197, 214, 230, 0.75)' : 'rgba(143, 163, 184, 0.35)';
      ctx.lineWidth = major ? 1.6 : 1;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
      ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
      ctx.stroke();
    }

    // Указатель.
    const span = this.max - this.min || 1;
    const ratio = Math.min(1, Math.max(0, (shown - this.min) / span));
    const angle = degToRad(-90 + ratio * 360);
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);
    ctx.strokeStyle = '#4cc2ff';
    ctx.lineWidth = Math.max(2.5, radius * 0.1);
    ctx.lineCap = 'round';
    ctx.shadowColor = 'rgba(76, 194, 255, 0.55)';
    ctx.shadowBlur = radius * 0.2;
    ctx.beginPath();
    ctx.moveTo(radius * 0.24, 0);
    ctx.lineTo(radius * 0.78, 0);
    ctx.stroke();
    ctx.restore();

    // Ступица.
    ctx.fillStyle = '#101a22';
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.22, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Значение.
    const text = this.hasData ? formatNumber(shown, this.decimals) : '--';
    ctx.fillStyle = '#e8f0f7';
    ctx.font = `600 ${Math.max(12, Math.round(h * 0.16))}px ${MONO}`;
    ctx.textBaseline = 'middle';
    ctx.fillText(this.unit ? `${text}${this.unit}` : text, cx, h * 0.885);
  }

  destroy() {
    if (this.sendTimer) clearTimeout(this.sendTimer);
    this.sendTimer = null;
    this.pendingSend = null;
  }
}

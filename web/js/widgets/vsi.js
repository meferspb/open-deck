/**
 * Вариометр (VSI): стрелка от 0 до ±2000 футов/мин.
 * Помощник `vsiAngle` вынесен отдельно — по нему есть тест.
 */

import { toFiniteNumber } from '../core/format.js';
import { CanvasSurface, Smoother, Widget, createCard, degToRad } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';

/**
 * Угол стрелки вариометра: 0 вверх, по часовой — набор, против — снижение.
 * @param {number} fpm
 * @param {number} [limit] предел шкалы, футов/мин
 */
export function vsiAngle(fpm, limit = 2000) {
  const value = Number.isFinite(fpm) ? fpm : 0;
  const clamped = Math.max(-limit, Math.min(limit, value));
  return (clamped / limit) * 90;
}

export class VsiWidget extends Widget {
  constructor(element, ctx, def) {
    super(element, ctx, def);
    this.card = createCard(element, 'vsi');
    this.surface = new CanvasSurface(this.card);
    this.limit = Number(this.options.limit) > 0 ? Number(this.options.limit) : 2000;
    this.value = new Smoother(0, 0.2);
    this.hasData = false;
  }

  update(state, now = performance.now()) {
    const value = toFiniteNumber(this.bindingValue(state, 'value'));
    this.hasData = value !== null;
    if (this.hasData) this.value.update(value, now);
    this.surface.resize();
    this.draw();
  }

  draw() {
    const { ctx, width: w, height: h } = this.surface;
    ctx.clearRect(0, 0, w, h);
    if (w < 24 || h < 24) return;

    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.max(10, Math.min(w, h) / 2 - Math.min(w, h) * 0.03);
    const fpm = this.hasData ? this.value.value : 0;

    ctx.save();
    ctx.translate(cx, cy);

    // Шкала: деления каждые limit/10, подписи 5 и 10 по обе стороны.
    for (let i = -10; i <= 10; i += 1) {
      const angle = (i / 10) * 90;
      const major = i % 5 === 0;
      const rad = degToRad(angle - 90);
      const inner = radius * (major ? 0.78 : 0.84);
      const outer = radius * 0.92;
      ctx.beginPath();
      ctx.moveTo(Math.cos(rad) * inner, Math.sin(rad) * inner);
      ctx.lineTo(Math.cos(rad) * outer, Math.sin(rad) * outer);
      ctx.strokeStyle = major ? 'rgba(214, 232, 245, 0.9)' : 'rgba(148, 180, 205, 0.55)';
      ctx.lineWidth = major ? Math.max(1.4, radius * 0.02) : Math.max(1, radius * 0.011);
      ctx.stroke();

      if (major && i !== 0) {
        ctx.fillStyle = 'rgba(214, 232, 245, 0.9)';
        ctx.font = `600 ${Math.max(8, Math.round(radius * 0.14))}px ${MONO}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const labelRadius = radius * 0.64;
        ctx.fillText(String(Math.abs(i / 5)), Math.cos(rad) * labelRadius, Math.sin(rad) * labelRadius);
      }
    }

    // Подписи направления.
    ctx.fillStyle = 'rgba(143, 163, 184, 0.9)';
    ctx.font = `600 ${Math.max(7, Math.round(radius * 0.1))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.fillText('UP', 0, -radius * 0.45);
    ctx.fillText('DN', 0, radius * 0.5);

    // Стрелка.
    ctx.save();
    ctx.rotate(vsiAngle(fpm, this.limit) * (Math.PI / 180));
    ctx.strokeStyle = '#ffcf4a';
    ctx.lineWidth = Math.max(2, radius * 0.03);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, radius * 0.12);
    ctx.lineTo(0, -radius * 0.8);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, -radius * 0.8);
    ctx.lineTo(-radius * 0.05, -radius * 0.66);
    ctx.lineTo(radius * 0.05, -radius * 0.66);
    ctx.closePath();
    ctx.fillStyle = '#ffcf4a';
    ctx.fill();
    ctx.restore();

    // Ось и цифровое значение.
    ctx.beginPath();
    ctx.arc(0, 0, Math.max(2, radius * 0.05), 0, Math.PI * 2);
    ctx.fillStyle = '#8fa3b8';
    ctx.fill();

    ctx.fillStyle = this.hasData ? '#d6e8f5' : 'rgba(143, 163, 184, 0.6)';
    ctx.font = `600 ${Math.max(9, Math.round(radius * 0.16))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.hasData ? formatFpm(fpm) : '---', 0, radius * 0.28);

    ctx.fillStyle = 'rgba(143, 163, 184, 0.75)';
    ctx.font = `600 ${Math.max(6, Math.round(radius * 0.08))}px ${MONO}`;
    ctx.fillText('VERTICAL SPEED', 0, radius * 0.62);
    ctx.restore();

    // Обод.
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = Math.max(1.5, radius * 0.02);
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.stroke();

    // Цветовая зона: набор — зелёный, снижение — янтарный.
    if (this.hasData && Math.abs(fpm) > this.limit * 1.05) {
      ctx.fillStyle = 'rgba(255, 93, 93, 0.16)';
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

/** @param {number} fpm */
export function formatFpm(fpm) {
  const rounded = Math.round(fpm / 10) * 10;
  if (Math.abs(rounded) < 20) return '0';
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded)}`;
}

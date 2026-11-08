/**
 * Авиагоризонт: canvas, лестница тангажа, шкала и указатель крена.
 * Прибор не «прыгает»: углы проходят через экспоненциальное сглаживание.
 */

import { toFiniteNumber } from '../core/format.js';
import { t } from '../core/i18n.js';
import { CanvasSurface, Smoother, Widget, createCard, degToRad } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';

export class AttitudeWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    this.card = createCard(element, 'attitude');
    this.surface = new CanvasSurface(this.card);
    this.pitch = new Smoother(0, 0.16);
    this.bank = new Smoother(0, 0.16);
    this.hasData = false;
  }

  update(state, now = performance.now()) {
    const pitch = toFiniteNumber(this.bindingValue(state, 'pitch'));
    const bank = toFiniteNumber(this.bindingValue(state, 'bank'));
    this.hasData = pitch !== null && bank !== null;

    if (this.hasData) {
      this.pitch.update(pitch, now);
      this.bank.update(bank, now);
    }

    if (!this.surface.resize()) {
      // размер не изменился — перерисовываем всё равно, прибор анимируется
    }
    this.draw();
  }

  draw() {
    const { ctx, width: w, height: h } = this.surface;
    ctx.clearRect(0, 0, w, h);
    if (w < 24 || h < 24) return;

    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.max(10, Math.min(w, h) / 2 - Math.min(w, h) * 0.035);
    const pitch = this.hasData ? this.pitch.value : 0;
    const bank = this.hasData ? this.bank.value : 0;

    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.clip();

    if (!this.hasData) {
      this.drawPlaceholder(ctx, cx, cy, radius);
    } else {
      this.drawHorizon(ctx, cx, cy, radius, pitch, bank);
    }

    ctx.restore();

    // Обод прибора поверх всего.
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = Math.max(1.5, radius * 0.02);
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.stroke();
    ctx.restore();
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} cx
   * @param {number} cy
   * @param {number} radius
   * @param {number} pitch
   * @param {number} bank
   */
  drawHorizon(ctx, cx, cy, radius, pitch, bank) {
    const pxPerDeg = radius / 30;

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-degToRad(bank));
    ctx.translate(0, pitch * pxPerDeg);

    const span = radius * 3;

    const sky = ctx.createLinearGradient(0, -span, 0, 0);
    sky.addColorStop(0, '#0a4a7a');
    sky.addColorStop(1, '#3d9ad8');
    ctx.fillStyle = sky;
    ctx.fillRect(-span, -span, span * 2, span);

    const ground = ctx.createLinearGradient(0, 0, 0, span);
    ground.addColorStop(0, '#8a5a2b');
    ground.addColorStop(1, '#2f1b0c');
    ctx.fillStyle = ground;
    ctx.fillRect(-span, 0, span * 2, span);

    // Линия горизонта.
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.95)';
    ctx.lineWidth = Math.max(1.5, radius * 0.012);
    ctx.beginPath();
    ctx.moveTo(-span, 0);
    ctx.lineTo(span, 0);
    ctx.stroke();

    // Лестница тангажа.
    const labelFont = Math.max(8, Math.round(radius * 0.085));
    ctx.font = `600 ${labelFont}px ${MONO}`;
    ctx.textBaseline = 'middle';

    for (let deg = -30; deg <= 30; deg += 5) {
      if (deg === 0) continue;
      const y = -deg * pxPerDeg;
      const major = deg % 10 === 0;
      const half = radius * (major ? 0.36 : 0.17);

      ctx.strokeStyle = major ? 'rgba(255, 255, 255, 0.92)' : 'rgba(255, 255, 255, 0.55)';
      ctx.lineWidth = major ? Math.max(1.4, radius * 0.011) : Math.max(1, radius * 0.007);
      ctx.beginPath();
      ctx.moveTo(-half, y);
      ctx.lineTo(half, y);
      ctx.stroke();

      if (major && Math.abs(deg) >= 10) {
        ctx.fillStyle = 'rgba(255, 255, 255, 0.92)';
        ctx.textAlign = 'right';
        ctx.fillText(String(Math.abs(deg)), -half - radius * 0.05, y);
        ctx.textAlign = 'left';
        ctx.fillText(String(Math.abs(deg)), half + radius * 0.05, y);
      }
    }
    ctx.restore();

    // Неподвижная шкала крена.
    ctx.save();
    ctx.translate(cx, cy);
    for (const deg of [-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60]) {
      const angle = degToRad(deg - 90);
      const inner = radius * (deg === 0 ? 0.85 : 0.9);
      const outer = radius * 0.97;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * inner, Math.sin(angle) * inner);
      ctx.lineTo(Math.cos(angle) * outer, Math.sin(angle) * outer);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.72)';
      ctx.lineWidth = deg === 0 ? Math.max(2, radius * 0.016) : Math.max(1, radius * 0.01);
      ctx.stroke();
    }

    // Указатель крена, привязанный к горизонту.
    ctx.rotate(degToRad(bank));
    ctx.beginPath();
    ctx.moveTo(0, -radius * 0.79);
    ctx.lineTo(-radius * 0.05, -radius * 0.9);
    ctx.lineTo(radius * 0.05, -radius * 0.9);
    ctx.closePath();
    ctx.fillStyle = '#ffcf4a';
    ctx.fill();
    ctx.restore();

    // Символ самолёта (неподвижный).
    ctx.save();
    ctx.translate(cx, cy);
    ctx.strokeStyle = '#ffcf4a';
    ctx.lineWidth = Math.max(2, radius * 0.036);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-radius * 0.62, 0);
    ctx.lineTo(-radius * 0.2, 0);
    ctx.moveTo(radius * 0.2, 0);
    ctx.lineTo(radius * 0.62, 0);
    ctx.stroke();
    ctx.fillStyle = '#ffcf4a';
    ctx.beginPath();
    ctx.arc(0, 0, Math.max(1.6, radius * 0.045), 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Блики стекла.
    const glass = ctx.createRadialGradient(cx, cy - radius * 0.5, radius * 0.1, cx, cy, radius);
    glass.addColorStop(0, 'rgba(255, 255, 255, 0.12)');
    glass.addColorStop(0.55, 'rgba(255, 255, 255, 0.02)');
    glass.addColorStop(1, 'rgba(0, 0, 0, 0.25)');
    ctx.fillStyle = glass;
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} cx
   * @param {number} cy
   * @param {number} radius
   */
  drawPlaceholder(ctx, cx, cy, radius) {
    const fill = ctx.createLinearGradient(cx, cy - radius, cx, cy + radius);
    fill.addColorStop(0, 'rgba(28, 38, 48, 0.9)');
    fill.addColorStop(1, 'rgba(12, 17, 22, 0.95)');
    ctx.fillStyle = fill;
    ctx.fillRect(cx - radius, cy - radius, radius * 2, radius * 2);

    ctx.save();
    ctx.setLineDash([radius * 0.08, radius * 0.06]);
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(cx - radius * 0.7, cy);
    ctx.lineTo(cx + radius * 0.7, cy);
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = 'rgba(143, 163, 184, 0.8)';
    ctx.font = `600 ${Math.max(9, Math.round(radius * 0.11))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(t('widget.noData'), cx, cy + radius * 0.32);
  }
}

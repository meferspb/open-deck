/**
 * Круговая шкала (тахометр, топливо, скорость): дуга 270°, зоны, красная
 * линия, стрелка со сглаживанием и цифровое значение в нижнем разрыве.
 */

import { formatNumber, toFiniteNumber } from '../core/format.js';
import { CanvasSurface, Smoother, TONE_COLORS, Widget, createCard } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';
const START = Math.PI * 0.75;
const SWEEP = Math.PI * 1.5;

export class RadialGaugeWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    this.card = createCard(element, 'gauge');
    this.surface = new CanvasSurface(this.card);

    const min = Number(this.options.min ?? 0);
    const max = Number(this.options.max ?? 100);
    this.min = Number.isFinite(min) ? min : 0;
    this.max = Number.isFinite(max) && max > this.min ? max : this.min + 1;
    this.decimals = Number.isFinite(Number(this.options.decimals)) ? Number(this.options.decimals) : 0;
    this.unit = typeof this.options.unit === 'string' ? this.options.unit : '';
    this.majorIntervals = Math.min(12, Math.max(1, Math.round(Number(this.options.majorTicks ?? 5))));
    this.minorPerMajor = Math.min(5, Math.max(1, Math.round(Number(this.options.minorTicks ?? 4))));

    this.needle = new Smoother(this.min, 0.14);
    this.hasData = false;
  }

  update(state, now = performance.now()) {
    const raw = toFiniteNumber(this.bindingValue(state, 'value'));
    this.hasData = raw !== null;
    if (this.hasData) {
      this.needle.update(Math.min(this.max, Math.max(this.min, raw)), now);
    }
    this.surface.resize();
    this.draw();
  }

  /** @param {number} value */
  angleFor(value) {
    const ratio = (value - this.min) / (this.max - this.min);
    return START + SWEEP * Math.min(1, Math.max(0, ratio));
  }

  draw() {
    const { ctx, width: w, height: h } = this.surface;
    ctx.clearRect(0, 0, w, h);
    if (w < 40 || h < 40) return;

    const cx = w / 2;
    const cy = h * 0.52;
    const radius = Math.max(16, Math.min(w * 0.44, h * 0.42));

    this.drawDial(ctx, cx, cy, radius);

    if (this.hasData) {
      this.drawNeedle(ctx, cx, cy, radius);
    }
    this.drawValue(ctx, cx, cy, radius);
  }

  drawDial(ctx, cx, cy, radius) {
    ctx.lineCap = 'round';

    // Дорожка шкалы.
    ctx.lineWidth = Math.max(4, radius * 0.07);
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.86, START, START + SWEEP);
    ctx.stroke();

    // Цветовые зоны.
    const zones = Array.isArray(this.options.zones) ? this.options.zones : [];
    ctx.lineWidth = Math.max(3, radius * 0.05);
    for (const zone of zones) {
      const from = Math.max(this.min, Number(zone?.from));
      const to = Math.min(this.max, Number(zone?.to));
      if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) continue;
      ctx.strokeStyle = TONE_COLORS[zone?.tone] ?? TONE_COLORS.warn;
      ctx.globalAlpha = 0.5;
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 0.86, this.angleFor(from), this.angleFor(to));
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Красная линия.
    const redline = Number(this.options.redline);
    if (Number.isFinite(redline) && redline > this.min && redline < this.max) {
      ctx.strokeStyle = TONE_COLORS.danger;
      ctx.lineWidth = Math.max(3, radius * 0.045);
      ctx.beginPath();
      ctx.arc(cx, cy, radius * 0.86, this.angleFor(redline), this.angleFor(this.max));
      ctx.stroke();
    }

    // Деления и подписи.
    const steps = this.majorIntervals * this.minorPerMajor;
    const labelFont = Math.max(8, Math.round(radius * 0.1));
    for (let i = 0; i <= steps; i += 1) {
      const value = this.min + ((this.max - this.min) * i) / steps;
      const major = i % this.minorPerMajor === 0;
      const angle = this.angleFor(value);

      const inner = radius * (major ? 0.9 : 0.93);
      const outer = radius * 0.99;
      ctx.strokeStyle = major ? 'rgba(232, 240, 247, 0.8)' : 'rgba(143, 163, 184, 0.45)';
      ctx.lineWidth = major ? Math.max(1.5, radius * 0.012) : Math.max(1, radius * 0.008);
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
      ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
      ctx.stroke();

      if (major) {
        ctx.fillStyle = 'rgba(197, 214, 230, 0.85)';
        ctx.font = `500 ${labelFont}px ${MONO}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        const labelRadius = radius * 0.77;
        ctx.fillText(
          formatNumber(value, 0),
          cx + Math.cos(angle) * labelRadius,
          cy + Math.sin(angle) * labelRadius,
        );
      }
    }
  }

  drawNeedle(ctx, cx, cy, radius) {
    const angle = this.angleFor(this.needle.value);

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(angle);

    ctx.shadowColor = 'rgba(0, 0, 0, 0.55)';
    ctx.shadowBlur = radius * 0.08;
    ctx.beginPath();
    ctx.moveTo(-radius * 0.13, 0);
    ctx.lineTo(0, -radius * 0.045);
    ctx.lineTo(radius * 0.8, 0);
    ctx.lineTo(0, radius * 0.045);
    ctx.closePath();
    ctx.fillStyle = '#f2f7fb';
    ctx.fill();
    ctx.restore();

    // Ступица.
    const hub = ctx.createRadialGradient(cx - radius * 0.02, cy - radius * 0.02, 1, cx, cy, radius * 0.08);
    hub.addColorStop(0, '#dfe9f2');
    hub.addColorStop(1, '#5d7083');
    ctx.fillStyle = hub;
    ctx.beginPath();
    ctx.arc(cx, cy, Math.max(3, radius * 0.07), 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = 'rgba(8, 12, 16, 0.8)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  drawValue(ctx, cx, cy, radius) {
    const text = this.hasData ? formatNumber(this.needle.value, this.decimals) : '--';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = this.hasData ? '#e8f0f7' : '#647689';
    ctx.font = `600 ${Math.max(11, Math.round(radius * 0.3))}px ${MONO}`;
    ctx.fillText(text, cx, cy + radius * 0.46);

    if (this.unit) {
      ctx.fillStyle = 'rgba(143, 163, 184, 0.85)';
      ctx.font = `500 ${Math.max(8, Math.round(radius * 0.12))}px ${MONO}`;
      ctx.fillText(this.unit, cx, cy + radius * 0.7);
    }
  }
}

/**
 * Курсоуказатель: вращающаяся картушка, неподвижная метка курса и «жучок»
 * заданного курса. `headingRotation` вынесен для тестов.
 */

import { toFiniteNumber } from '../core/format.js';
import { CanvasSurface, Smoother, Widget, createCard, degToRad } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';
const CARDINAL = { 0: 'N', 90: 'E', 180: 'S', 270: 'W' };

/** Нормализует угол в диапазон [0, 360). */
export function normalizeHeading(degrees) {
  const value = Number.isFinite(degrees) ? degrees : 0;
  return ((value % 360) + 360) % 360;
}

/**
 * Угол поворота картушки: курс растёт — картушка крутится против часовой.
 * @param {number} headingDeg
 */
export function headingRotation(headingDeg) {
  return -normalizeHeading(headingDeg);
}

export class HeadingWidget extends Widget {
  constructor(element, ctx, def) {
    super(element, ctx, def);
    this.card = createCard(element, 'heading');
    this.surface = new CanvasSurface(this.card);
    this.heading = new Smoother(0, 0.25);
    this.bug = new Smoother(0, 0.25);
    this.hasData = false;
    this.hasBug = false;
  }

  update(state, now = performance.now()) {
    const heading = toFiniteNumber(this.bindingValue(state, 'heading'));
    const bug = toFiniteNumber(this.bindingValue(state, 'bug'));
    this.hasData = heading !== null;
    this.hasBug = bug !== null;
    if (this.hasData) this.heading.update(heading, now);
    if (this.hasBug) this.bug.update(bug, now);
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
    const heading = normalizeHeading(this.hasData ? this.heading.value : 0);

    ctx.save();
    ctx.translate(cx, cy);

    // Картушка.
    ctx.save();
    ctx.rotate(degToRad(headingRotation(heading)));

    for (let deg = 0; deg < 360; deg += 5) {
      const angle = degToRad(deg - 90);
      const major = deg % 30 === 0;
      const mid = deg % 10 === 0;
      const inner = radius * (major ? 0.74 : mid ? 0.8 : 0.85);
      const outer = radius * 0.9;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * inner, Math.sin(angle) * inner);
      ctx.lineTo(Math.cos(angle) * outer, Math.sin(angle) * outer);
      ctx.strokeStyle = major ? 'rgba(232, 244, 255, 0.95)' : 'rgba(148, 180, 205, 0.55)';
      ctx.lineWidth = major ? Math.max(1.5, radius * 0.022) : Math.max(1, radius * 0.01);
      ctx.stroke();

      if (major) {
        const labelRadius = radius * 0.6;
        const label = CARDINAL[deg] ?? String(deg / 10);
        ctx.fillStyle = CARDINAL[deg] ? '#ffcf4a' : 'rgba(232, 244, 255, 0.95)';
        ctx.font = `700 ${Math.max(9, Math.round(radius * (CARDINAL[deg] ? 0.22 : 0.17)))}px ${MONO}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(label, Math.cos(angle) * labelRadius, Math.sin(angle) * labelRadius);
      }
    }

    // Жучок заданного курса вращается вместе с картушкой.
    if (this.hasBug) {
      ctx.save();
      ctx.rotate(degToRad(this.bug.value - heading));
      ctx.beginPath();
      ctx.moveTo(0, -radius * 0.98);
      ctx.lineTo(-radius * 0.07, -radius * 0.84);
      ctx.lineTo(radius * 0.07, -radius * 0.84);
      ctx.closePath();
      ctx.fillStyle = '#4cc2ff';
      ctx.fill();
      ctx.restore();
    }
    ctx.restore();

    // Неподвижный символ самолёта и метка курса.
    ctx.strokeStyle = '#ffcf4a';
    ctx.lineWidth = Math.max(2, radius * 0.03);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(-radius * 0.42, 0);
    ctx.lineTo(-radius * 0.14, 0);
    ctx.moveTo(radius * 0.14, 0);
    ctx.lineTo(radius * 0.42, 0);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(0, -radius * 0.99);
    ctx.lineTo(-radius * 0.05, -radius * 0.88);
    ctx.lineTo(radius * 0.05, -radius * 0.88);
    ctx.closePath();
    ctx.fillStyle = '#ffcf4a';
    ctx.fill();

    // Цифровое значение.
    ctx.fillStyle = this.hasData ? '#d6e8f5' : 'rgba(143, 163, 184, 0.6)';
    ctx.font = `600 ${Math.max(10, Math.round(radius * 0.19))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.hasData ? `${String(Math.round(heading) % 360).padStart(3, '0')}°` : '---', 0, radius * 0.42);
    ctx.restore();

    // Обод.
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = Math.max(1.5, radius * 0.02);
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.stroke();
  }
}

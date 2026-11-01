/**
 * Высотомер: три стрелки (сотни, тысячи, десятки тысяч) как на классике.
 * `altimeterPointers` — чистый помощник, покрыт тестом.
 */

import { CanvasSurface, Smoother, Widget, createCard, degToRad } from './base.js';

const MONO = '"Cascadia Mono", "Consolas", monospace';

/**
 * Углы трёх стрелок высотомера в градусах.
 * @param {number} altitudeFt
 */
export function altimeterPointers(altitudeFt) {
  const altitude = Number.isFinite(altitudeFt) ? altitudeFt : 0;
  const positive = Math.max(0, altitude);
  return {
    hundreds: (((positive / 100) % 10) * 36 + 360) % 360,
    thousands: (((positive / 1000) % 10) * 36 + 360) % 360,
    tenThousands: (((positive / 10000) % 10) * 36 + 360) % 360,
  };
}

export class AltimeterWidget extends Widget {
  constructor(element, ctx, def) {
    super(element, ctx, def);
    this.card = createCard(element, 'altimeter');
    this.surface = new CanvasSurface(this.card);
    this.altitude = new Smoother(0, 0.25);
    this.hasData = false;
  }

  update(state, now = performance.now()) {
    const value = Number(this.bindingValue(state, 'value'));
    this.hasData = Number.isFinite(value);
    if (this.hasData) this.altitude.update(value, now);
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
    const altitude = this.hasData ? Math.max(0, this.altitude.value) : 0;
    const pointers = altimeterPointers(altitude);

    ctx.save();
    ctx.translate(cx, cy);

    // Внешняя шкала: 50 делений по 100 футов, подписи 0..9 через 1000.
    for (let i = 0; i < 50; i += 1) {
      const angle = degToRad((i / 50) * 360 - 90);
      const major = i % 5 === 0;
      const inner = radius * (major ? 0.8 : 0.86);
      const outer = radius * 0.92;
      ctx.beginPath();
      ctx.moveTo(Math.cos(angle) * inner, Math.sin(angle) * inner);
      ctx.lineTo(Math.cos(angle) * outer, Math.sin(angle) * outer);
      ctx.strokeStyle = major ? 'rgba(214, 232, 245, 0.9)' : 'rgba(148, 180, 205, 0.5)';
      ctx.lineWidth = major ? Math.max(1.3, radius * 0.018) : Math.max(1, radius * 0.009);
      ctx.stroke();

      if (major) {
        const labelAngle = degToRad((i / 50) * 360 - 90);
        const labelRadius = radius * 0.68;
        ctx.fillStyle = 'rgba(214, 232, 245, 0.92)';
        ctx.font = `600 ${Math.max(9, Math.round(radius * 0.16))}px ${MONO}`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i / 5), Math.cos(labelAngle) * labelRadius, Math.sin(labelAngle) * labelRadius);
      }
    }

    // Десятки тысяч — короткая широкая стрелка.
    this.needle(ctx, radius * 0.45, pointers.tenThousands, radius * 0.035, '#ff8a5b');

    // Тысячи — средняя.
    this.needle(ctx, radius * 0.66, pointers.thousands, radius * 0.026, '#ffcf4a');

    // Сотни — длинная тонкая.
    this.needle(ctx, radius * 0.84, pointers.hundreds, radius * 0.014, '#e8f4ff');

    // Центральный колпачок.
    ctx.beginPath();
    ctx.arc(0, 0, Math.max(2.4, radius * 0.045), 0, Math.PI * 2);
    ctx.fillStyle = '#8fa3b8';
    ctx.fill();

    // Цифровое табло внизу.
    ctx.fillStyle = 'rgba(9, 15, 21, 0.75)';
    const boxW = radius * 1.15;
    const boxH = radius * 0.3;
    ctx.beginPath();
    ctx.roundRect(-boxW / 2, radius * 0.38, boxW, boxH, radius * 0.06);
    ctx.fill();
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = this.hasData ? '#d6e8f5' : 'rgba(143, 163, 184, 0.6)';
    ctx.font = `600 ${Math.max(9, Math.round(radius * 0.16))}px ${MONO}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(this.hasData ? String(Math.round(altitude)) : '---', 0, radius * 0.38 + boxH / 2);

    ctx.fillStyle = 'rgba(143, 163, 184, 0.7)';
    ctx.font = `600 ${Math.max(6, Math.round(radius * 0.075))}px ${MONO}`;
    ctx.fillText('ALT · FT', 0, radius * 0.8);
    ctx.restore();

    // Обод.
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.lineWidth = Math.max(1.5, radius * 0.02);
    ctx.strokeStyle = 'rgba(148, 180, 205, 0.35)';
    ctx.stroke();
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} length
   * @param {number} angleDeg
   * @param {number} width
   * @param {string} color
   */
  needle(ctx, length, angleDeg, width, color) {
    ctx.save();
    ctx.rotate(degToRad(angleDeg));
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(0, length * 0.16);
    ctx.lineTo(0, -length);
    ctx.stroke();
    ctx.restore();
  }
}

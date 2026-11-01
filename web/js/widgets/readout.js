/**
 * Цифровое табло: подпись, значение, единица. Опциональная «тревога»
 * по порогу подсвечивает значение янтарным.
 */

import { formatNumber } from '../core/format.js';
import { Widget, createCard, h } from './base.js';

export class ReadoutWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--readout');

    this.card = createCard(element, 'readout');
    this.captionEl = h('span', 'readout__caption', this.options.caption ?? def.label ?? '');
    this.valueEl = h('span', 'readout__value', '--');
    this.unitEl = h('span', 'readout__unit', this.options.unit ?? '');

    const row = h('span', 'readout__row');
    row.append(this.valueEl, this.unitEl);
    this.card.append(this.captionEl, row);

    const decimals = Number(this.options.decimals);
    this.decimals = Number.isFinite(decimals) ? decimals : 0;
    this.alarm = this.options.alarm ?? null;
  }

  update(state) {
    const raw = this.bindingValue(state, 'value');
    const text = formatNumber(raw, this.decimals);
    if (this.valueEl.textContent !== text) this.valueEl.textContent = text;

    const alarm = this.isAlarm(raw);
    if (alarm !== this.card.classList.contains('is-alarm')) {
      this.card.classList.toggle('is-alarm', alarm);
    }
  }

  /** @param {unknown} raw */
  isAlarm(raw) {
    if (!this.alarm || !Number.isFinite(raw)) return false;
    const below = Number(this.alarm.below);
    const above = Number(this.alarm.above);
    if (Number.isFinite(below) && raw < below) return true;
    if (Number.isFinite(above) && raw > above) return true;
    return false;
  }
}

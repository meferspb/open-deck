/**
 * Табло-лампа: загорается, когда условие истинно. `invert` нужен для
 * индикаторов вида «BUS OFF», которые горят при выключенном питании.
 */

import { Widget, createCard, h } from './base.js';
import { t } from '../core/i18n.js';

export class AnnunciatorWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--annunciator');

    this.caption = this.options.caption ?? def.label ?? '';
    this.invert = Boolean(this.options.invert);
    this.card = createCard(element, 'lamp');
    this.card.dataset.tone = this.options.tone === 'warn' || this.options.tone === 'ok' ? this.options.tone : 'danger';
    this.card.setAttribute('role', 'img');
    this.card.append(h('span', 'lamp__caption', this.caption));

    this.lit = false;
    this.updateAria();
  }

  update(state) {
    const raw = this.bindingValue(state, 'active');
    // null — данных нет: не зажигаем лампу, даже если задан invert.
    const lit = raw == null ? false : this.invert ? !raw : Boolean(raw);
    if (lit === this.lit) return;
    this.lit = lit;
    this.card.classList.toggle('is-lit', lit);
    this.updateAria();
  }

  updateAria() {
    this.card.setAttribute(
      'aria-label',
      `${this.caption}: ${this.lit ? t('widget.lampOn') : t('widget.lampOff')}`,
    );
  }
}

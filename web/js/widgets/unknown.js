/**
 * Заглушка для прибора, который есть в профиле, но не поддержан клиентом.
 * Лучше показать предупреждение, чем молча потерять элемент панели.
 */

import { Widget, createCard, h } from './base.js';

export class UnknownWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--unknown');
    const card = createCard(element, 'unknown');
    card.append(
      h('span', 'unknown__type', String(def?.type ?? 'unknown')),
      h('span', 'unknown__type', 'тип прибора не поддержан'),
    );
  }
}

/**
 * Тумблер: отправляет команду на шлюз и ждёт подтверждения.
 * Визуальное состояние всегда следует за телеметрией, а не за кликом —
 * так панель не «врёт» при отказе симулятора.
 */

import { Widget, h } from './base.js';

export class ToggleSwitchWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--switch');

    this.caption = this.options.caption ?? def.label ?? 'SWITCH';
    this.onLabel = this.options.onLabel ?? 'ON';
    this.offLabel = this.options.offLabel ?? 'OFF';
    this.action = this.def.command?.action ?? 'set';
    this.commandKey = this.def.command?.key ?? null;

    this.button = h('button', 'card switch');
    this.button.type = 'button';
    this.button.setAttribute('role', 'switch');
    this.button.setAttribute('aria-checked', 'false');

    this.track = h('span', 'switch__track');
    this.track.append(h('span', 'switch__knob'));
    this.stateEl = h('span', 'switch__state', this.offLabel);

    const row = h('span', 'switch__row');
    row.append(this.track, this.stateEl);
    this.button.append(h('span', 'switch__caption', this.caption), row);
    element.append(this.button);

    this.current = false;
    this.pendingTarget = null;
    /** @type {ReturnType<typeof setTimeout> | null} */
    this.pendingTimer = null;

    this.button.addEventListener('click', () => this.onClick());
  }

  onClick() {
    if (this.pendingTarget !== null || !this.commandKey) return;
    const target = !this.current;
    this.setPending(target);

    const value = this.action === 'toggle' ? true : target;
    this.ctx
      .command(this.commandKey, value)
      .then(() => {
        // Итоговое состояние придёт в телеметрии — ждём его.
      })
      .catch((error) => {
        this.clearPending();
        this.ctx.notify?.(`${this.caption}: ${error?.message ?? 'команда не выполнена'}`);
      });
  }

  /** @param {boolean} target */
  setPending(target) {
    this.pendingTarget = target;
    this.button.classList.add('is-pending');
    this.button.setAttribute('aria-busy', 'true');
    if (this.pendingTimer) clearTimeout(this.pendingTimer);
    this.pendingTimer = setTimeout(() => {
      this.ctx.notify?.(`${this.caption}: телеметрия не подтвердила команду`);
      this.clearPending();
    }, 2500);
  }

  clearPending() {
    this.pendingTarget = null;
    this.button.classList.remove('is-pending');
    this.button.removeAttribute('aria-busy');
    if (this.pendingTimer) clearTimeout(this.pendingTimer);
    this.pendingTimer = null;
  }

  update(state) {
    const on = Boolean(this.bindingValue(state, 'state'));
    if (on !== this.current) {
      this.current = on;
      this.button.classList.toggle('is-on', on);
      this.button.setAttribute('aria-checked', String(on));
      this.stateEl.textContent = on ? this.onLabel : this.offLabel;
    }
    if (this.pendingTarget !== null && on === this.pendingTarget) this.clearPending();
  }

  destroy() {
    this.clearPending();
    this.button.remove();
  }
}

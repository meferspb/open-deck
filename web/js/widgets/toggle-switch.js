/**
 * Тумблер: отправляет команду на шлюз и ждёт подтверждения.
 * Визуальное состояние всегда следует за телеметрией, а не за кликом —
 * так панель не «врёт» при отказе симулятора.
 */

import { Widget, h, haptic } from './base.js';
import { t } from '../core/i18n.js';

export class ToggleSwitchWidget extends Widget {
  /**
   * @param {HTMLElement} element
   * @param {any} ctx
   * @param {any} def
   */
  constructor(element, ctx, def) {
    super(element, ctx, def);
    element.classList.add('widget--switch');

    this.caption = this.options.caption ?? def.label ?? t('editor.widget.switch.toggle');
    this.onLabel = this.options.onLabel ?? t('widget.on');
    this.offLabel = this.options.offLabel ?? t('widget.off');
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
    /** @type {ReturnType<typeof setTimeout> | null} */
    this.rejectedTimer = null;

    this.button.addEventListener('click', () => this.onClick());
  }

  onClick() {
    if (this.pendingTarget !== null || !this.commandKey) return;
    haptic();
    const target = !this.current;
    this.setPending(target);

    const value = this.action === 'toggle' ? true : target;
    this.ctx
      .command(this.commandKey, value)
      .then((ack) => {
        if (ack?.ok === false) this.markRejected(ack.error || t('widget.commandNotExecuted'));
        // Итоговое состояние придёт в телеметрии — ждём его.
      })
      .catch((error) => {
        this.clearPending();
        this.markRejected(error?.message ?? t('widget.commandNotExecuted'));
      });
  }

  /** @param {boolean} target */
  setPending(target) {
    this.pendingTarget = target;
    this.el.classList.add('is-pending');
    this.button.classList.add('is-pending');
    this.button.setAttribute('aria-busy', 'true');
    if (this.pendingTimer) clearTimeout(this.pendingTimer);
    this.pendingTimer = setTimeout(() => this.clearPending(), 800);
  }

  markRejected(message) {
    this.el.classList.add('is-rejected');
    this.button.classList.add('is-rejected');
    if (this.rejectedTimer) clearTimeout(this.rejectedTimer);
    this.rejectedTimer = setTimeout(() => {
      this.el.classList.remove('is-rejected');
      this.button.classList.remove('is-rejected');
    }, 600);
    this.ctx.notify?.(`${this.caption}: ${message}`);
  }

  clearPending() {
    this.pendingTarget = null;
    this.el.classList.remove('is-pending');
    this.button.classList.remove('is-pending');
    this.button.removeAttribute('aria-busy');
    if (this.pendingTimer) clearTimeout(this.pendingTimer);
    this.pendingTimer = null;
  }

  update(state) {
    const raw = this.bindingValue(state, 'state');
    const on = raw == null ? null : Boolean(raw);
    if (on !== this.current) {
      this.current = on;
      this.button.classList.toggle('is-on', on === true);
      this.button.setAttribute('aria-checked', String(on === true));
      this.stateEl.textContent = on == null ? '--' : on ? this.onLabel : this.offLabel;
    }
    if (this.pendingTarget !== null && on === this.pendingTarget) this.clearPending();
  }

  destroy() {
    this.clearPending();
    if (this.rejectedTimer) clearTimeout(this.rejectedTimer);
    this.button.remove();
  }
}

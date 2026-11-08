/**
 * Раскладка панели: создаёт экземпляры приборов по профилю и ведёт
 * единый кадровый цикл. Смена форм-фактора просто пересчитывает проценты.
 */

import { rectFor } from '../core/layout.js';
import { t } from '../core/i18n.js';
import { createWidgetInstance } from '../widgets/registry.js';

/**
 * @param {{
 *   panel: HTMLElement,
 *   getState: () => any,
 *   command: (key: string, value: unknown) => Promise<any>,
 *   notify?: (message: string) => void,
 * }} options
 */
export function createPanelView({ panel, getState, command, notify }) {
  /** @type {any} */
  let profile = null;
  let deviceClass = 'tablet-lg';
  /** @type {Array<{def: any, element: HTMLElement, instance: any, broken: boolean}>} */
  let items = [];
  let frameId = 0;
  let state = null;

  const widgetContext = {
    getState: () => state,
    command: (key, value) => command(key, value),
    notify: (message) => notify?.(message),
  };

  function clear() {
    if (frameId) cancelAnimationFrame(frameId);
    frameId = 0;
    for (const item of items) {
      try {
        item.instance.destroy();
      } catch (error) {
        console.warn('widget destroy failed', item.def?.id, error);
      }
    }
    items = [];
    panel.replaceChildren();
    state = null;
  }

  function layout() {
    const width = panel.clientWidth;
    const height = panel.clientHeight;
    for (const { def, element } of items) {
      const rect = rectFor(def, deviceClass);
      element.style.left = `${rect.x * 100}%`;
      element.style.top = `${rect.y * 100}%`;
      element.style.width = `${rect.w * 100}%`;
      element.style.height = `${rect.h * 100}%`;
      element.style.setProperty('--w', `${Math.round(rect.w * width)}px`);
      element.style.setProperty('--h', `${Math.round(rect.h * height)}px`);
    }
  }

  function frame(now) {
    frameId = requestAnimationFrame(frame);
    state = getState();
    if (!state) return;

    for (const item of items) {
      if (item.broken) continue;
      try {
        item.instance.update(state, now);
      } catch (error) {
        item.broken = true;
        console.error('widget update failed', item.def?.id, error);
        notify?.(t('error.widgetRender', { id: item.def?.id ?? '' }));
      }
    }
  }

  const resizeObserver = new ResizeObserver(() => {
    if (observing) layout();
  });

  // Наблюдатель живёт дольше одного профиля: destroy() отключает его,
  // а mount() подключает заново, иначе после разблокировки/перезагрузки
  // панель перестала бы реагировать на изменение размера.
  let observing = false;
  function ensureObserver() {
    if (observing) return;
    resizeObserver.observe(panel);
    observing = true;
  }

  return {
    /** @param {any} nextProfile */
    mount(nextProfile) {
      clear();
      profile = nextProfile;
      panel.style.setProperty('--panel-bg', profile?.panel?.background ?? '#0b1117');
      panel.style.setProperty('--grid', String(Number(profile?.panel?.gridSize) || 8));

      for (const def of profile?.widgets ?? []) {
        const element = document.createElement('div');
        element.className = `widget widget--${String(def.type).replace(/[^a-z0-9]+/gi, '-')}`;
        element.dataset.widgetId = def.id;
        element.setAttribute('role', 'group');
        element.setAttribute('aria-label', def.label || def.id);
        panel.append(element);

        const instance = createWidgetInstance(def, element, widgetContext);
        try {
          instance.mount();
        } catch (error) {
          console.error('widget mount failed', def.id, error);
        }
        items.push({ def, element, instance, broken: false });
      }

      if (profile?.panel?.footer) {
        const footer = document.createElement('div');
        footer.className = 'panel__footer';
        footer.textContent = profile.panel.footer;
        panel.append(footer);
      }

      layout();
      ensureObserver();
      frameId = requestAnimationFrame(frame);
    },

    /** @param {string} nextClass */
    setDeviceClass(nextClass) {
      deviceClass = nextClass;
      layout();
    },

    destroy() {
      clear();
      observing = false;
      resizeObserver.disconnect();
      profile = null;
    },

    get profile() {
      return profile;
    },
  };
}

/**
 * Комфорт на кокпите: яркость панели (день/сумерки/ночь) и режим киоска.
 *
 * Яркость хранится в localStorage и применяется атрибутом на <html>:
 * CSS гасит только сцену с приборами, интерфейс остаётся читаемым.
 * Киоск скрывает верхнюю панель и статус-бар — для планшета, закреплённого
 * на панели самолёта; выход по Esc или кнопке в углу.
 */

import { onLocaleChange, t } from '../core/i18n.js';
import { THEMES, THEME_STORAGE_KEY, isTheme, nextTheme } from './theme.js';

export const BRIGHTNESS_LEVELS = Object.freeze([
  { id: 'full', value: 1, label: '100%' },
  { id: 'dim', value: 0.72, label: '72%' },
  { id: 'night', value: 0.45, label: '45%' },
]);

const STORAGE_KEY = 'open-deck:brightness';

/** @param {string} id */
export function nextBrightness(id) {
  const index = BRIGHTNESS_LEVELS.findIndex((level) => level.id === id);
  return BRIGHTNESS_LEVELS[(index + 1) % BRIGHTNESS_LEVELS.length].id;
}

/** @param {string} id */
export function brightnessLabel(id) {
  return BRIGHTNESS_LEVELS.find((level) => level.id === id)?.label ?? BRIGHTNESS_LEVELS[0].label;
}

/**
 * @param {{
 *   brightnessButton: HTMLElement,
 *   themeButton: HTMLElement,
 *   kioskButton: HTMLElement,
 *   exitButton: HTMLElement,
 *   onKioskChange?: (on: boolean) => void,
 *   notify?: (message: string) => void,
 * }} options
 */
export function createComfort({
  brightnessButton,
  themeButton,
  kioskButton,
  exitButton,
  onKioskChange,
  notify,
}) {
  const root = document.documentElement;
  let kiosk = false;

  function storedBrightness() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (BRIGHTNESS_LEVELS.some((level) => level.id === stored)) return stored;
    } catch {
      /* localStorage может быть выключен */
    }
    return BRIGHTNESS_LEVELS[0].id;
  }

  function applyBrightness(id, { announce = true } = {}) {
    root.dataset.brightness = id;
    const label = brightnessLabel(id);
    brightnessButton.title = t('comfort.brightnessTitle', { label });
    brightnessButton.setAttribute('aria-label', t('comfort.brightnessAria', { label }));
    brightnessButton.dataset.level = id;
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* игнорируем */
    }
    if (announce && id !== 'full' && notify) {
      notify(t('comfort.brightnessNotify', { label }));
    }
  }

  function cycleBrightness() {
    applyBrightness(nextBrightness(root.dataset.brightness ?? BRIGHTNESS_LEVELS[0].id));
  }

  function storedTheme() {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (isTheme(stored)) return stored;
    } catch {
      /* localStorage может быть выключен */
    }
    return THEMES[0].id;
  }

  function applyTheme(id, { announce = true } = {}) {
    const theme = isTheme(id) ? id : THEMES[0].id;
    root.dataset.theme = theme;
    themeButton.dataset.theme = theme;
    const label = t(`theme.${theme}`);
    themeButton.title = t('comfort.themeTitle', { theme: label });
    themeButton.setAttribute('aria-label', t('comfort.themeAria', { theme: label }));
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* игнорируем */
    }
    if (announce && notify) notify(t('comfort.themeNotify', { theme: label }));
    window.dispatchEvent(new CustomEvent('open-deck:theme', { detail: { theme } }));
  }

  function cycleTheme() {
    applyTheme(nextTheme(root.dataset.theme ?? THEMES[0].id));
  }

  function setKiosk(next, { announce = true } = {}) {
    kiosk = next;
    document.body.classList.toggle('kiosk', kiosk);
    exitButton.hidden = !kiosk;
    kioskButton.setAttribute('aria-pressed', String(kiosk));
    kioskButton.title = kiosk ? t('comfort.kioskOnTitle') : t('comfort.kioskOffTitle');
    onKioskChange?.(kiosk);
    if (announce && notify) {
      notify(kiosk ? t('comfort.kioskOnNotify') : t('comfort.kioskOffNotify'));
    }
  }

  onLocaleChange(() => {
    applyBrightness(root.dataset.brightness ?? BRIGHTNESS_LEVELS[0].id, { announce: false });
    applyTheme(root.dataset.theme ?? THEMES[0].id, { announce: false });
    kioskButton.title = kiosk ? t('comfort.kioskOnTitle') : t('comfort.kioskOffTitle');
  });

  brightnessButton.addEventListener('click', cycleBrightness);
  themeButton.addEventListener('click', cycleTheme);
  kioskButton.addEventListener('click', () => setKiosk(!kiosk));
  exitButton.addEventListener('click', () => setKiosk(false));

  document.addEventListener('keydown', (event) => {
    const tag = event.target?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    const key = event.key.toLowerCase();
    if (key === 'b') {
      event.preventDefault();
      cycleBrightness();
    } else if (key === 'n') {
      event.preventDefault();
      cycleTheme();
    } else if (key === 'f') {
      event.preventDefault();
      setKiosk(!kiosk);
    } else if (key === 'escape' && kiosk) {
      event.preventDefault();
      setKiosk(false);
    }
  });

  applyBrightness(storedBrightness());
  applyTheme(storedTheme());

  return {
    cycleBrightness,
    cycleTheme,
    setKiosk,
    get brightness() {
      return root.dataset.brightness;
    },
    get theme() {
      return root.dataset.theme;
    },
    get kiosk() {
      return kiosk;
    },
  };
}

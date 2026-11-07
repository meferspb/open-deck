/**
 * Комфорт на кокпите: яркость панели (день/сумерки/ночь) и режим киоска.
 *
 * Яркость хранится в localStorage и применяется атрибутом на <html>:
 * CSS гасит только сцену с приборами, интерфейс остаётся читаемым.
 * Киоск скрывает верхнюю панель и статус-бар — для планшета, закреплённого
 * на панели самолёта; выход по Esc или кнопке в углу.
 */

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
 *   kioskButton: HTMLElement,
 *   exitButton: HTMLElement,
 *   onKioskChange?: (on: boolean) => void,
 *   notify?: (message: string) => void,
 * }} options
 */
export function createComfort({ brightnessButton, kioskButton, exitButton, onKioskChange, notify }) {
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

  function applyBrightness(id) {
    root.dataset.brightness = id;
    const label = brightnessLabel(id);
    brightnessButton.title = `Яркость панели: ${label} (B)`;
    brightnessButton.setAttribute('aria-label', `Яркость панели: ${label}`);
    brightnessButton.dataset.level = id;
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* игнорируем */
    }
    if (id !== 'full' && notify) {
      notify(`Яркость панели: ${label}`);
    }
  }

  function cycleBrightness() {
    applyBrightness(nextBrightness(root.dataset.brightness ?? BRIGHTNESS_LEVELS[0].id));
  }

  function setKiosk(next, { announce = true } = {}) {
    kiosk = next;
    document.body.classList.toggle('kiosk', kiosk);
    exitButton.hidden = !kiosk;
    kioskButton.setAttribute('aria-pressed', String(kiosk));
    kioskButton.title = kiosk ? 'Выйти из режима киоска (Esc)' : 'Режим киоска — скрыть интерфейс (F)';
    onKioskChange?.(kiosk);
    if (announce && notify) {
      notify(kiosk ? 'Режим киоска: Esc — вернуть интерфейс' : 'Интерфейс восстановлен');
    }
  }

  brightnessButton.addEventListener('click', cycleBrightness);
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
    } else if (key === 'f') {
      event.preventDefault();
      setKiosk(!kiosk);
    } else if (key === 'escape' && kiosk) {
      event.preventDefault();
      setKiosk(false);
    }
  });

  applyBrightness(storedBrightness());

  return {
    cycleBrightness,
    setKiosk,
    get brightness() {
      return root.dataset.brightness;
    },
    get kiosk() {
      return kiosk;
    },
  };
}

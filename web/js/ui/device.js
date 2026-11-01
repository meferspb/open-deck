/**
 * Форм-факторы клиента. Размеры — логические CSS-пиксели «экрана устройства»:
 * именно в них профиль раскладывает приборы, поэтому превью на Windows-хосте
 * совпадает с тем, что увидит планшет.
 */

/** @typedef {{id: string, label: string, title: string, width: number, height: number, bezel: number, radius: number}} DevicePreset */

/** @type {Record<string, DevicePreset>} */
export const DEVICE_PRESETS = {
  phone: {
    id: 'phone',
    label: 'Phone',
    title: 'Телефон',
    width: 390,
    height: 844,
    bezel: 10,
    radius: 46,
  },
  'tablet-sm': {
    id: 'tablet-sm',
    label: 'Small Tablet',
    title: 'Малый планшет',
    width: 1024,
    height: 768,
    bezel: 14,
    radius: 30,
  },
  'tablet-lg': {
    id: 'tablet-lg',
    label: 'Large Tablet',
    title: 'Большой планшет',
    width: 1366,
    height: 1024,
    bezel: 16,
    radius: 32,
  },
};

export const DEVICE_ORDER = Object.freeze(['phone', 'tablet-sm', 'tablet-lg']);

/**
 * @param {string} id
 * @returns {DevicePreset}
 */
export function getPreset(id) {
  return DEVICE_PRESETS[id] ?? DEVICE_PRESETS['tablet-lg'];
}

/**
 * Класс раскладки по ширине окна — используется, когда пользователь
 * не выбрал форм-фактор вручную (и для первого запуска).
 * @param {number} width
 * @returns {string}
 */
export function detectDeviceClass(width) {
  if (width < 600) return 'phone';
  if (width < 1200) return 'tablet-sm';
  return 'tablet-lg';
}

/**
 * Превью с рамкой показываем только на большом экране: на реальном
 * телефоне панель должна занимать весь экран, а не рисоваться в макете.
 * @param {{innerWidth: number, matchMedia?: (q: string) => MediaQueryList}} [view]
 */
export function shouldUseFrame(view = window) {
  return view.innerWidth >= 900;
}

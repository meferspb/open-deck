/**
 * Геометрия раскладки: профиль задаёт прямоугольники в долях панели (0..1),
 * а клиент переводит их в проценты. Так один профиль работает на любом
 * экране, а переопределения по форм-фактору задают лишь отличия.
 */

export const FORM_FACTORS = Object.freeze(['phone', 'tablet-sm', 'tablet-lg']);

/**
 * @param {number} value
 * @param {number} min
 * @param {number} max
 */
export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Приводит прямоугольник к безопасному виду: числа, границы 0..1,
 * ненулевые размеры, ничего не выходит за панель.
 * @param {{x?: unknown, y?: unknown, w?: unknown, h?: unknown}} [rect]
 * @returns {{x: number, y: number, w: number, h: number}}
 */
export function normalizeRect(rect = {}) {
  const toNumber = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const x = clamp(toNumber(rect.x, 0), 0, 1);
  const y = clamp(toNumber(rect.y, 0), 0, 1);
  let w = clamp(toNumber(rect.w, 1), 0.001, 1);
  let h = clamp(toNumber(rect.h, 1), 0.001, 1);

  if (x + w > 1) w = Math.max(0.001, 1 - x);
  if (y + h > 1) h = Math.max(0.001, 1 - y);

  return { x, y, w, h };
}

/**
 * Привязка координаты к сетке: `snapToGrid(0.317, 0.01) === 0.32`.
 * Шаг 0 или меньше отключает привязку.
 * @param {number} value
 * @param {number} step
 */
export function snapToGrid(value, step) {
  if (!(step > 0) || !Number.isFinite(value)) return value;
  return Math.round(value / step) * step;
}

/**
 * Прямоугольник виджета для конкретного форм-фактора:
 * `layout.base` — база, `layout[formFactor]` — только отличия.
 * @param {any} widget
 * @param {string} formFactor
 */
export function rectFor(widget, formFactor) {
  const layout = widget?.layout ?? {};
  const base = layout.base ?? { x: 0, y: 0, w: 1, h: 1 };
  const override = layout?.[formFactor];
  return normalizeRect(override ? { ...base, ...override } : base);
}

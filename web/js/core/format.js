/**
 * Форматирование значений телеметрии для приборов.
 * Чистые функции без DOM — их же используют тесты (node --test).
 */

/** @param {unknown} value */
export function isFiniteNumber(value) {
  return typeof value === 'number' && Number.isFinite(value);
}

/**
 * Число для дисплея: без разделителей тысяч (как на настоящих приборах),
 * с фиксированным числом знаков. Нет данных — прочерк.
 * @param {unknown} value
 * @param {number} [decimals]
 */
export function formatNumber(value, decimals = 0) {
  if (!isFiniteNumber(value)) return '--';
  const safe = Math.min(3, Math.max(0, Math.round(Number(decimals) || 0)));
  return value.toFixed(safe);
}

/**
 * @param {unknown} value
 * @param {string} [onLabel]
 * @param {string} [offLabel]
 */
export function formatBoolean(value, onLabel = 'ON', offLabel = 'OFF') {
  return value ? onLabel : offLabel;
}

/**
 * Значение по ключу телеметрии (ключи плоские, с точками внутри).
 * @param {Record<string, unknown> | null | undefined} values
 * @param {string} key
 */
export function readValue(values, key) {
  if (!values || typeof key !== 'string') return undefined;
  return values[key];
}

/**
 * Угол в диапазоне [0, 360).
 * @param {number} degrees
 */
export function normalizeHeading(degrees) {
  if (!isFiniteNumber(degrees)) return 0;
  return ((degrees % 360) + 360) % 360;
}

/** Cockpit colour themes. Kept free of DOM so it can be unit-tested. */

export const THEMES = Object.freeze([
  { id: 'day', label: 'Day' },
  { id: 'night-red', label: 'Night red' },
  { id: 'amber', label: 'Amber' },
]);

export const THEME_STORAGE_KEY = 'open-deck:theme';

/** @param {string} id */
export function nextTheme(id) {
  const index = THEMES.findIndex((theme) => theme.id === id);
  return THEMES[(index + 1) % THEMES.length].id;
}

/** @param {string} id */
export function themeLabel(id) {
  return THEMES.find((theme) => theme.id === id)?.label ?? THEMES[0].label;
}

/** @param {unknown} value */
export function isTheme(value) {
  return typeof value === 'string' && THEMES.some((theme) => theme.id === value);
}

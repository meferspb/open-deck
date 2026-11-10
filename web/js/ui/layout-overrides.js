/** Pure helpers for editor layout overrides (easy to unit-test). */

export const OVERRIDE_OFFSET = 0.02;

/** @param {any} widget @param {string} formFactor */
export function hasFormFactorOverride(widget, formFactor) {
  return Boolean(widget?.layout?.[formFactor]);
}

/** @param {any} widget @param {string} formFactor */
export function resetFormFactorOverride(widget, formFactor) {
  if (!hasFormFactorOverride(widget, formFactor)) return false;
  delete widget.layout[formFactor];
  return true;
}

/**
 * Clamps an offset rectangle inside the panel.
 * @param {{x?: number, y?: number}} rect
 */
export function offsetOverrideRect(rect, delta = OVERRIDE_OFFSET) {
  if (rect && typeof rect === 'object') {
    if (typeof rect.x === 'number') rect.x = Number((rect.x + delta).toFixed(4));
    if (typeof rect.y === 'number') rect.y = Number((rect.y + delta).toFixed(4));
  }
  return rect;
}

/** @param {Array<{id: string}>} widgets @param {string} baseId */
export function uniqueWidgetId(widgets, baseId) {
  let id = baseId;
  let n = 1;
  const taken = new Set(widgets.map((widget) => widget.id));
  while (taken.has(id)) id = `${baseId}-${++n}`;
  return id;
}

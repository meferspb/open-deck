/**
 * Тесты геометрии раскладки (чистые функции, node:test).
 * Запуск: node --test tests/web/
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { clamp, normalizeRect, rectFor, snapToGrid, FORM_FACTORS } from '../../web/js/core/layout.js';

test('clamp ограничивает значение', () => {
  assert.equal(clamp(5, 0, 10), 5);
  assert.equal(clamp(-1, 0, 10), 0);
  assert.equal(clamp(11, 0, 10), 10);
});

test('normalizeRect приводит типы и границы', () => {
  const rect = normalizeRect({ x: '0.5', y: 0, w: 2, h: -1 });
  assert.equal(rect.x, 0.5);
  assert.equal(rect.y, 0);
  assert.equal(rect.w, 0.5, 'w обрезается до 1 - x');
  assert.equal(rect.h, 0.001, 'h приводится к минимальному >0');
});

test('rectFor возвращает base при отсутствии переопределения', () => {
  const widget = { layout: { base: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } } };
  const rect = rectFor(widget, 'phone');
  assert.deepEqual(rect, { x: 0.1, y: 0.2, w: 0.3, h: 0.4 });
});

test('rectFor сливает переопределение поверх base', () => {
  const widget = {
    layout: {
      base: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 },
      phone: { x: 0.5, h: 0.6 },
    },
  };
  const rect = rectFor(widget, 'phone');
  assert.equal(rect.x, 0.5);
  assert.equal(rect.y, 0.2, 'y наследуется из base');
  assert.equal(rect.w, 0.3, 'w наследуется из base');
  assert.equal(rect.h, 0.6);
});

test('FORM_FACTORS содержит три пресета', () => {
  assert.deepEqual(FORM_FACTORS, ['phone', 'tablet-sm', 'tablet-lg']);
});

test('snapToGrid привязывает к шагу и не портит выключенную сетку', () => {
  assert.equal(snapToGrid(0.317, 0.01), 0.32);
  assert.equal(snapToGrid(0.314, 0.01), 0.31);
  assert.equal(snapToGrid(0.317, 0), 0.317);
  assert.equal(snapToGrid(Number.NaN, 0.01), Number.NaN);
});

/**
 * Тесты форматирования значений (чистые функции, node:test).
 * Запуск: node --test tests/web/
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
  formatBoolean,
  formatNumber,
  isFiniteNumber,
  normalizeHeading,
  readValue,
} from '../../web/js/core/format.js';

test('isFiniteNumber', () => {
  assert.equal(isFiniteNumber(1), true);
  assert.equal(isFiniteNumber(0), true);
  assert.equal(isFiniteNumber(NaN), false);
  assert.equal(isFiniteNumber(Infinity), false);
  assert.equal(isFiniteNumber('1'), false);
  assert.equal(isFiniteNumber(null), false);
});

test('formatNumber фиксирует знаки', () => {
  assert.equal(formatNumber(108.456, 0), '108');
  assert.equal(formatNumber(24.197, 1), '24.2');
  assert.equal(formatNumber(1, 2), '1.00');
});

test('formatNumber отдаёт прочерк для нечисла', () => {
  assert.equal(formatNumber(undefined), '--');
  assert.equal(formatNumber(null), '--');
  assert.equal(formatNumber('abc'), '--');
});

test('formatNumber ограничивает decimals 0..3', () => {
  assert.equal(formatNumber(1.23456, 9), '1.235');
  assert.equal(formatNumber(1.23456, -1), '1');
});

test('formatBoolean', () => {
  assert.equal(formatBoolean(true), 'ON');
  assert.equal(formatBoolean(false), 'OFF');
  assert.equal(formatBoolean(true, 'ВКЛ', 'ВЫКЛ'), 'ВКЛ');
});

test('readValue по плоскому ключу', () => {
  const values = { 'power.batteryMaster': true, 'speed.iasKt': 108 };
  assert.equal(readValue(values, 'power.batteryMaster'), true);
  assert.equal(readValue(values, 'missing'), undefined);
  assert.equal(readValue(null, 'x'), undefined);
});

test('normalizeHeading заворачивает в [0, 360)', () => {
  assert.equal(normalizeHeading(0), 0);
  assert.equal(normalizeHeading(360), 0);
  assert.equal(normalizeHeading(370), 10);
  assert.equal(normalizeHeading(-10), 350);
  assert.equal(normalizeHeading(NaN), 0);
});

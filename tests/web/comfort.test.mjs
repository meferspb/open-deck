import test from 'node:test';
import assert from 'node:assert/strict';

import { BRIGHTNESS_LEVELS, brightnessLabel, nextBrightness } from '../../web/js/ui/comfort.js';

test('nextBrightness перебирает три уровня по кругу', () => {
  assert.equal(nextBrightness('full'), 'dim');
  assert.equal(nextBrightness('dim'), 'night');
  assert.equal(nextBrightness('night'), 'full');
});

test('nextBrightness устойчив к неизвестному уровню', () => {
  assert.equal(nextBrightness('unknown'), 'full');
  assert.equal(nextBrightness(''), 'full');
});

test('brightnessLabel отдаёт проценты', () => {
  assert.equal(brightnessLabel('full'), '100%');
  assert.equal(brightnessLabel('dim'), '72%');
  assert.equal(brightnessLabel('night'), '45%');
  assert.equal(brightnessLabel('unknown'), '100%');
});

test('уровни яркости идут от светлого к тёмному', () => {
  const values = BRIGHTNESS_LEVELS.map((level) => level.value);
  assert.deepEqual(values, [...values].sort((a, b) => b - a));
});

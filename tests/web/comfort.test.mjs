import assert from 'node:assert/strict';
import test from 'node:test';

import { BRIGHTNESS_LEVELS, brightnessLabel, nextBrightness } from '../../web/js/ui/comfort.js';
import { THEMES, isTheme, nextTheme, themeLabel } from '../../web/js/ui/theme.js';

test('nextBrightness cycles three levels', () => {
  assert.equal(nextBrightness('full'), 'dim');
  assert.equal(nextBrightness('dim'), 'night');
  assert.equal(nextBrightness('night'), 'full');
});

test('nextBrightness tolerates unknown levels', () => {
  assert.equal(nextBrightness('unknown'), 'full');
  assert.equal(nextBrightness(''), 'full');
});

test('brightnessLabel returns percentages', () => {
  assert.equal(brightnessLabel('full'), '100%');
  assert.equal(brightnessLabel('dim'), '72%');
  assert.equal(brightnessLabel('night'), '45%');
  assert.equal(brightnessLabel('unknown'), '100%');
});

test('brightness levels are ordered from light to dark', () => {
  const values = BRIGHTNESS_LEVELS.map((level) => level.value);
  assert.deepEqual(values, [...values].sort((a, b) => b - a));
});

test('cockpit themes expose day, night-red and amber', () => {
  assert.deepEqual(
    THEMES.map((theme) => theme.id),
    ['day', 'night-red', 'amber'],
  );
  assert.equal(isTheme('night-red'), true);
  assert.equal(isTheme('unknown'), false);
});

test('theme cycle wraps and labels are stable', () => {
  assert.equal(nextTheme('day'), 'night-red');
  assert.equal(nextTheme('night-red'), 'amber');
  assert.equal(nextTheme('amber'), 'day');
  assert.equal(themeLabel('amber'), 'Amber');
  assert.equal(themeLabel('unknown'), 'Day');
});

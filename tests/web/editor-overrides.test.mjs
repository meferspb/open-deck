import assert from 'node:assert/strict';
import test from 'node:test';

import {
  hasFormFactorOverride,
  offsetOverrideRect,
  resetFormFactorOverride,
  uniqueWidgetId,
} from '../../web/js/ui/layout-overrides.js';

test('form-factor override is detected and reset', () => {
  const widget = {
    layout: {
      base: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 },
      phone: { x: 0.5 },
    },
  };
  assert.equal(hasFormFactorOverride(widget, 'phone'), true);
  assert.equal(hasFormFactorOverride(widget, 'tablet-sm'), false);
  assert.equal(resetFormFactorOverride(widget, 'phone'), true);
  assert.deepEqual(widget.layout.phone, undefined);
  assert.equal(hasFormFactorOverride(widget, 'phone'), false);
});

test('resetting a missing override is a no-op', () => {
  const widget = { layout: { base: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } } };
  assert.equal(resetFormFactorOverride(widget, 'phone'), false);
  assert.deepEqual(widget.layout, { base: { x: 0.1, y: 0.2, w: 0.3, h: 0.4 } });
});

test('override offsets are applied in place', () => {
  const rect = { x: 0.1, y: 0.2 };
  assert.equal(offsetOverrideRect(rect, 0.02), rect);
  assert.equal(rect.x, 0.12);
  assert.equal(rect.y, 0.22);
});

test('duplicate ids get a numeric suffix', () => {
  const widgets = [{ id: 'airspeed-copy' }, { id: 'airspeed-copy-2' }];
  assert.equal(uniqueWidgetId(widgets, 'airspeed'), 'airspeed');
  assert.equal(uniqueWidgetId(widgets, 'airspeed-copy'), 'airspeed-copy-3');
});

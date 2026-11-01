import test from 'node:test';
import assert from 'node:assert/strict';

import { altimeterPointers } from '../../web/js/widgets/altimeter.js';
import { headingRotation, normalizeHeading } from '../../web/js/widgets/heading.js';
import { formatFpm, vsiAngle } from '../../web/js/widgets/vsi.js';

test('vsiAngle: ноль вверх, набор по часовой', () => {
  assert.equal(vsiAngle(0), 0);
  assert.equal(vsiAngle(1000), 45);
  assert.equal(vsiAngle(2000), 90);
  assert.equal(vsiAngle(-1000), -45);
  assert.equal(vsiAngle(-2000), -90);
});

test('vsiAngle: ограничение и мусор', () => {
  assert.equal(vsiAngle(9000), 90);
  assert.equal(vsiAngle(-9000), -90);
  assert.equal(vsiAngle(Number.NaN), 0);
  assert.equal(vsiAngle(500, 1000), 45);
});

test('formatFpm: знак и округление до десятков', () => {
  assert.equal(formatFpm(0), '0');
  assert.equal(formatFpm(14), '0');
  assert.equal(formatFpm(423), '+420');
  assert.equal(formatFpm(-1354), '−1350');
});

test('altimeterPointers: три стрелки на своих местах', () => {
  const zero = altimeterPointers(0);
  assert.deepEqual(zero, { hundreds: 0, thousands: 0, tenThousands: 0 });

  const pointers = altimeterPointers(1234);
  assert.ok(Math.abs(pointers.hundreds - (2.34 * 36) % 360) < 1e-9);
  assert.ok(Math.abs(pointers.thousands - (1.234 * 36) % 360) < 1e-9);
  assert.ok(Math.abs(pointers.tenThousands - (0.1234 * 36) % 360) < 1e-9);
});

test('altimeterPointers: полный оборот стрелки сотен', () => {
  const a = altimeterPointers(0).hundreds;
  const b = altimeterPointers(1000).hundreds;
  assert.equal(a, b);
});

test('altimeterPointers: отрицательная высота не ломает шкалу', () => {
  assert.deepEqual(altimeterPointers(-50), { hundreds: 0, thousands: 0, tenThousands: 0 });
  assert.deepEqual(altimeterPointers(Number.NaN), { hundreds: 0, thousands: 0, tenThousands: 0 });
});

test('normalizeHeading приводит угол к 0..360', () => {
  assert.equal(normalizeHeading(0), 0);
  assert.equal(normalizeHeading(360), 0);
  assert.equal(normalizeHeading(730), 10);
  assert.equal(normalizeHeading(-30), 330);
  assert.equal(normalizeHeading(Number.NaN), 0);
});

test('headingRotation: картушка крутится против курса', () => {
  assert.equal(headingRotation(0), -0);
  assert.equal(headingRotation(90), -90);
  assert.equal(headingRotation(-90), -270);
  assert.equal(headingRotation(360), -0);
});

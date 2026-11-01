import test from 'node:test';
import assert from 'node:assert/strict';

import { isConnectionStale } from '../../web/js/core/socket.js';

test('isConnectionStale: свежие сообщения — соединение живо', () => {
  assert.equal(isConnectionStale(10_000, 9_900, 2_000), false);
  assert.equal(isConnectionStale(10_000, 10_000, 2_000), false);
});

test('isConnectionStale: тишина дольше порога — зависло', () => {
  assert.equal(isConnectionStale(10_000, 7_000, 2_000), true);
});

test('isConnectionStale: без единого сообщения не срабатывает', () => {
  assert.equal(isConnectionStale(10_000, 0, 2_000), false);
});

test('isConnectionStale: граница ровно в порог считается живой', () => {
  assert.equal(isConnectionStale(10_000, 8_000, 2_000), false);
});

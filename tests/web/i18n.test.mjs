import test from 'node:test';
import assert from 'node:assert/strict';

import {
  DEFAULT_LOCALE,
  LOCALE_ORDER,
  getDictionary,
  isSupportLabel,
  normalizeLocale,
  setLocale,
  t,
} from '../../web/js/core/i18n.js';

test('все локали содержат одинаковый набор ключей', () => {
  const base = Object.keys(getDictionary('en')).sort();
  for (const locale of LOCALE_ORDER) {
    assert.deepEqual(Object.keys(getDictionary(locale)).sort(), base, locale);
  }
});

test('normalizeLocale понимает региональные теги', () => {
  assert.equal(normalizeLocale('ru-RU'), 'ru');
  assert.equal(normalizeLocale('zh-CN'), 'zh');
  assert.equal(normalizeLocale('de_DE'), 'de');
  assert.equal(normalizeLocale('fr'), null);
  assert.equal(normalizeLocale(''), null);
});

test('t переводит и подставляет параметры', () => {
  setLocale('en');
  assert.equal(DEFAULT_LOCALE, 'en');
  assert.equal(t('common.save'), 'Save');
  assert.equal(t('panel.loadingProfile', { name: 'C172' }), 'Loading “C172”…');
  setLocale('ru');
  assert.equal(t('common.save'), 'Сохранить');
  assert.equal(t('panel.loadingProfile', { name: 'C172' }), 'Загрузка «C172»…');
  setLocale('en');
});

test('isSupportLabel принимает локализованные подписи и отвергает подмену', () => {
  for (const locale of LOCALE_ORDER) {
    assert.equal(isSupportLabel(getDictionary(locale)['donation.support']), true, locale);
  }
  assert.equal(isSupportLabel('totally custom text'), false);
  assert.equal(isSupportLabel(''), false);
});

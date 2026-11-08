/**
 * Клиентская проверка целостности интерфейса.
 *
 * Задача — не дать изменить/скрыть блок поддержки автора без реакции
 * приложения. Авторитетная проверка выполняется на Windows-хосте
 * (см. msfs_gateway/integrity.py), клиент лишь сверяет её результат и
 * следит, чтобы блок оставался видимым.
 *
 * Ограничение (честно): в браузере пользователь контролирует код, поэтому
 * это барьер от случайной/намеренной правки, а не криптографическая защита.
 */

import { api } from '../core/api.js';
import { isSupportLabel, t } from '../core/i18n.js';

const BADGE_SELECTOR = '[data-donation-badge]';

/** @param {Element | null} element */
function isVisiblyRendered(element) {
  if (!element || !element.isConnected) return false;
  if (element.hasAttribute('hidden') || element.getAttribute('aria-hidden') === 'true') return false;

  const style = getComputedStyle(element);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  if (Number(style.opacity) < 0.2) return false;

  const rect = element.getBoundingClientRect();
  return rect.width >= 40 && rect.height >= 16;
}

/**
 * @returns {Promise<{ok: boolean, reason: string, code: string, report: any}>}
 */
export async function verifyUiIntegrity() {
  let report = null;
  try {
    report = await api.integrity();
  } catch (error) {
    return {
      ok: false,
      reason: t('integrity.unreachable'),
      code: 'gateway_unreachable',
      report: null,
    };
  }

  if (!report?.verified) {
    return {
      ok: false,
      reason: t('integrity.hostFailed'),
      code: 'host_integrity_failed',
      report,
    };
  }

  const badge = document.querySelector(BADGE_SELECTOR);
  if (!badge) {
    return {
      ok: false,
      reason: t('integrity.badgeMissing'),
      code: 'badge_missing',
      report,
    };
  }
  if (!isVisiblyRendered(badge)) {
    return {
      ok: false,
      reason: t('integrity.badgeHidden'),
      code: 'badge_hidden',
      report,
    };
  }
  if (!isSupportLabel(badge.textContent || '')) {
    return {
      ok: false,
      reason: t('integrity.badgeText'),
      code: 'badge_text_changed',
      report,
    };
  }

  return { ok: true, reason: '', code: 'ok', report };
}

/**
 * Следит за блоком поддержки после старта: удаление или скрытие
 * мгновенно блокирует интерфейс.
 *
 * @param {{badge: Element | null, onViolation: (reason: string, code: string) => void, intervalMs?: number}} options
 */
export function watchIntegrity({ badge, onViolation, intervalMs = 2500 }) {
  let triggered = false;

  const check = () => {
    if (triggered) return;
    if (!badge || !isVisiblyRendered(badge) || !isSupportLabel(badge.textContent || '')) {
      triggered = true;
      onViolation(t('integrity.badgeTampered'), 'badge_tampered');
    }
  };

  const bodyObserver = new MutationObserver(check);
  bodyObserver.observe(document.body, { childList: true, subtree: true });

  let badgeObserver = null;
  if (badge) {
    badgeObserver = new MutationObserver(check);
    badgeObserver.observe(badge, {
      attributes: true,
      attributeFilter: ['hidden', 'style', 'class', 'aria-hidden'],
    });
  }

  const timer = setInterval(check, intervalMs);

  return () => {
    bodyObserver.disconnect();
    badgeObserver?.disconnect();
    clearInterval(timer);
  };
}

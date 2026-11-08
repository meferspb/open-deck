/**
 * Блок поддержки автора (требование лицензии).
 *
 * Реквизиты не хранятся в клиенте: они приходят с шлюза из
 * `config/donation.json`, который проверяется по хешу при старте хоста.
 * Клиент только отображает то, что прислал хост.
 */

import { api } from '../core/api.js';
import { applyDonationLinksFromConfig } from '../core/donation-links.js';
import { isSupportLabel, onLocaleChange, t } from '../core/i18n.js';

/**
 * @param {{chip: HTMLElement, dialog: HTMLDialogElement, body: HTMLElement, closeButton: HTMLElement}} refs
 */
export function createDonation({ chip, dialog, body, closeButton }) {
  let config = null;

  function updateChip() {
    const label = chip.querySelector('span');
    const configured = typeof config?.chipLabel === 'string' ? config.chipLabel.trim() : '';
    // Стандартную подпись из конфига переводим; нестандартную оставляем автором.
    if (label) {
      label.textContent = configured && !isSupportLabel(configured)
        ? configured
        : t('donation.support');
    }
    chip.title = config?.title
      ? t('donation.chipTitleWith', { title: config.title })
      : t('donation.chipTitle');
  }

  async function load() {
    try {
      config = await api.donation();
    } catch {
      config = null;
    }

    applyDonationLinksFromConfig(config);
    updateChip();
  }

  function copyValue(text, button) {
    const done = () => {
      button.textContent = t('donation.copied');
      setTimeout(() => {
        button.textContent = t('donation.copy');
      }, 1400);
    };
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(done).catch(() => selectText(button));
    } else {
      selectText(button);
    }
  }

  function selectText(element) {
    const value = element.previousElementSibling;
    if (value) {
      const range = document.createRange();
      range.selectNodeContents(value);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  }

  function renderBody() {
    body.replaceChildren();

    const intro = document.createElement('p');
    intro.className = 'donation-card__note';
    intro.textContent = config?.message ?? t('donation.noConfig');
    body.append(intro);

    const links = Array.isArray(config?.links) ? config.links : [];
    if (!links.length) {
      const empty = document.createElement('p');
      empty.className = 'donation-dialog__empty';
      empty.textContent = t('donation.noRequisites');
      body.append(empty);
    }

    for (const link of links) {
      const card = document.createElement('div');
      card.className = 'donation-card';

      const label = document.createElement('span');
      label.className = 'donation-card__label';
      label.textContent = String(link?.label ?? t('donation.labelFallback'));
      card.append(label);

      if (typeof link?.url === 'string' && /^https?:\/\//i.test(link.url)) {
        const anchor = document.createElement('a');
        anchor.href = link.url;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = link.url;
        card.append(anchor);
        if (typeof link.note === 'string' && link.note) {
          const note = document.createElement('span');
          note.className = 'donation-card__note';
          note.textContent = link.note;
          card.append(note);
        }
      } else if (typeof link?.value === 'string') {
        const value = document.createElement('code');
        value.className = 'donation-card__value';
        value.textContent = link.value;
        const copy = document.createElement('button');
        copy.type = 'button';
        copy.className = 'btn';
        copy.textContent = t('donation.copy');
        copy.addEventListener('click', () => copyValue(link.value, copy));
        card.append(value, copy);
      }
      body.append(card);
    }

    const meta = document.createElement('p');
    meta.className = 'donation-card__note';
    const author = typeof config?.author === 'string' && config.author
      ? config.author
      : t('donation.authorFallback');
    const updated = typeof config?.updatedAt === 'string' && config.updatedAt
      ? t('donation.updated', { date: config.updatedAt })
      : '';
    meta.textContent = `${author}${updated}`;
    body.append(meta);
  }

  function open() {
    renderBody();
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      dialog.setAttribute('open', '');
    }
  }

  function close() {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  }

  onLocaleChange(() => {
    updateChip();
    if (dialog.open) renderBody();
  });

  chip.addEventListener('click', open);
  closeButton.addEventListener('click', close);
  dialog.addEventListener('click', (event) => {
    if (event.target === dialog) close();
  });

  return {
    load,
    open,
    close,
    getConfig: () => config,
  };
}

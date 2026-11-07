/**
 * Блок поддержки автора (требование лицензии).
 *
 * Реквизиты не хранятся в клиенте: они приходят с шлюза из
 * `config/donation.json`, который проверяется по хешу при старте хоста.
 * Клиент только отображает то, что прислал хост.
 */

import { api } from '../core/api.js';
import { applyDonationLinksFromConfig } from '../core/donation-links.js';

/**
 * @param {{chip: HTMLElement, dialog: HTMLDialogElement, body: HTMLElement, closeButton: HTMLElement}} refs
 */
export function createDonation({ chip, dialog, body, closeButton }) {
  let config = null;

  async function load() {
    try {
      config = await api.donation();
    } catch {
      config = null;
    }

    applyDonationLinksFromConfig(config);
    const label = chip.querySelector('span');
    if (label && typeof config?.chipLabel === 'string' && config.chipLabel.trim()) {
      label.textContent = config.chipLabel;
    }
    chip.title = config?.title ? `${config.title} — поддержать автора` : 'Поддержать автора проекта';
  }

  function copyValue(text, button) {
    const done = () => {
      button.textContent = 'скопировано';
      setTimeout(() => {
        button.textContent = 'копировать';
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
    intro.textContent =
      config?.message ?? 'Реквизиты поддержки не настроены в config/donation.json на хосте.';
    body.append(intro);

    const links = Array.isArray(config?.links) ? config.links : [];
    if (!links.length) {
      const empty = document.createElement('p');
      empty.className = 'donation-dialog__empty';
      empty.textContent = 'Автор ещё не указал реквизиты — блок остаётся видимым по условиям лицензии.';
      body.append(empty);
    }

    for (const link of links) {
      const card = document.createElement('div');
      card.className = 'donation-card';

      const label = document.createElement('span');
      label.className = 'donation-card__label';
      label.textContent = String(link?.label ?? 'Поддержка');
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
        copy.textContent = 'копировать';
        copy.addEventListener('click', () => copyValue(link.value, copy));
        card.append(value, copy);
      }
      body.append(card);
    }

    const meta = document.createElement('p');
    meta.className = 'donation-card__note';
    const author = typeof config?.author === 'string' && config.author ? config.author : 'автор проекта';
    const updated = typeof config?.updatedAt === 'string' && config.updatedAt ? ` · обновлено ${config.updatedAt}` : '';
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

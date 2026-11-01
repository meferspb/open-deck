/**
 * Диалог «Подключить телефон»: QR-код адреса панели.
 *
 * Адрес берётся у шлюза (`/api/connect`) — он знает свои сетевые интерфейсы.
 * QR рисует сам хост (`/api/qr.svg`), поэтому клиенту не нужны сторонние
 * библиотеки и интернет.
 */

import { api } from '../core/api.js';

export function createConnect({
  button,
  dialog,
  closeButton,
  image,
  urlField,
  copyButton,
  altField,
  listField,
  notify,
}) {
  let loaded = false;
  let loading = false;
  let currentUrl = '';
  let scale = 6;
  let border = 4;
  /** Одноразовый токен для входа с телефона без ввода пароля. */
  let pairToken = '';

  function withQuery(url, params) {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}${params}`;
  }

  function phoneUrlFor(url) {
    const query = pairToken ? `device=phone&pair=${encodeURIComponent(pairToken)}` : 'device=phone';
    return withQuery(url, query);
  }

  function qrSource(url) {
    return `/api/qr.svg?text=${encodeURIComponent(url)}&scale=${scale}&border=${border}`;
  }

  function preload(src) {
    return new Promise((resolve, reject) => {
      const probe = new Image();
      probe.onload = resolve;
      probe.onerror = () => reject(new Error('не удалось построить QR-код'));
      probe.src = src;
    });
  }

  function renderList(urls, activeUrl) {
    if (!listField) return;
    listField.replaceChildren(
      ...urls.map((entry) => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'connect__alt-link';
        chip.dataset.url = entry.url;
        chip.textContent = entry.host;
        chip.title = entry.url;
        chip.setAttribute('aria-pressed', String(entry.url === activeUrl));
        chip.addEventListener('click', () => {
          selectUrl(entry.url).catch((error) => {
            if (notify) notify(`Не удалось переключить адрес: ${error.message}`);
          });
        });
        return chip;
      }),
    );
  }

  async function selectUrl(baseUrl) {
    const phoneUrl = phoneUrlFor(baseUrl);
    const src = qrSource(phoneUrl);
    await preload(src);

    image.src = src;
    image.alt = `QR-код адреса панели: ${phoneUrl}`;
    urlField.textContent = phoneUrl;
    currentUrl = phoneUrl;

    for (const chip of listField?.querySelectorAll('.connect__alt-link') ?? []) {
      chip.setAttribute('aria-pressed', String(chip.dataset.url === baseUrl));
    }
  }

  async function load() {
    if (loaded || loading) return;
    loading = true;
    urlField.textContent = 'получаем адрес…';

    try {
      const response = await fetch('/api/connect', { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`шлюз вернул ${response.status}`);
      const payload = await response.json();

      const urls = Array.isArray(payload.urls) ? payload.urls.filter((entry) => entry.url) : [];
      if (!urls.length) throw new Error('шлюз не сообщил ни одного адреса');

      scale = payload.qr?.scale ?? 6;
      border = payload.qr?.border ?? 4;

      // Если включён пароль, просим одноразовый QR-токен: телефон войдёт
      // одним сканированием. Без пароля всё работает по-прежнему.
      pairToken = '';
      try {
        const pair = await api.pair();
        if (pair?.required && typeof pair.token === 'string') pairToken = pair.token;
      } catch {
        // Одноразовый вход недоступен — покажем обычный адрес.
      }

      const primary = payload.primaryUrl || urls[0].url;
      renderList(urls, primary);
      await selectUrl(primary);

      const others = urls.map((entry) => entry.url).filter((url) => url !== primary);
      altField.textContent = pairToken
        ? 'QR действует 10 минут и входит без пароля. Если телефон в другой сети, выберите адрес выше.'
        : others.length
          ? 'Если телефон в другой сети, выберите адрес выше.'
          : '';

      loaded = true;
    } catch (error) {
      urlField.textContent = '—';
      if (notify) notify(`Не удалось подготовить QR: ${error.message}`);
    } finally {
      loading = false;
    }
  }

  async function copy() {
    const text = currentUrl || urlField.textContent;
    if (!text || text === '—') return;
    try {
      await navigator.clipboard.writeText(text);
      if (notify) notify('Адрес скопирован');
    } catch {
      // Буфер обмена может быть запрещён — выделяем текст как запасной вариант.
      const range = document.createRange();
      range.selectNodeContents(urlField);
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(range);
    }
  }

  function open() {
    if (!dialog.open) dialog.showModal();
    load();
  }

  button?.addEventListener('click', open);
  closeButton?.addEventListener('click', () => dialog.close());
  copyButton?.addEventListener('click', copy);
  dialog?.addEventListener('click', (event) => {
    if (event.target === dialog) dialog.close();
  });

  return { open, load, copy, selectUrl };
}

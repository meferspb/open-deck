/**
 * Конфиг-зависимые ссылки Donat в интерфейсах.
 *
 * Единственный источник реквизитов — config/donation.json на хосте; в HTML
 * остаётся только якорь с data-donation-link и текстом-заглушкой.
 */

function pickLink(links) {
  if (!Array.isArray(links)) return null;
  const donat = links.find((item) => /donat/i.test(String(item?.label ?? '')));
  const candidate = donat ?? links[0];
  return candidate && /^https?:\/\//i.test(String(candidate.url ?? '')) ? candidate : null;
}

/**
 * @param {{links?: Array<{label?: string, url?: string}>} | null} config
 * @param {ParentNode} [root]
 */
export function applyDonationLinksFromConfig(config, root = document) {
  const link = pickLink(config?.links);
  for (const anchor of root.querySelectorAll('[data-donation-link]')) {
    if (!(anchor instanceof HTMLAnchorElement)) continue;
    if (!link) {
      anchor.hidden = true;
      anchor.removeAttribute('href');
      continue;
    }
    anchor.hidden = false;
    anchor.href = link.url;
    anchor.textContent = String(link.label ?? 'Donat');
    anchor.target = '_blank';
    anchor.rel = 'noopener noreferrer';
  }
}

/** @param {ParentNode} [root] */
export async function hydrateDonationLinks(root = document) {
  try {
    const response = await fetch('/api/donation', {
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    applyDonationLinksFromConfig(await response.json(), root);
  } catch {
    applyDonationLinksFromConfig(null, root);
  }
}

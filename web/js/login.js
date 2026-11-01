/**
 * Страница входа: пароль → сессия (httponly-кука) → возврат на исходную страницу.
 *
 * Всё локально: ни одного внешнего запроса, кроме API этого же шлюза.
 * Пароль никогда не сохраняется в localStorage и не попадает в URL.
 */

const form = document.getElementById('login-form');
const input = document.getElementById('login-password');
const submit = document.getElementById('login-submit');
const reveal = document.getElementById('login-reveal');
const errorBox = document.getElementById('login-error');
const title = document.getElementById('login-title');
const note = document.getElementById('login-note');
const actions = document.getElementById('login-actions');
const continueLink = document.getElementById('login-continue');
const logoutButton = document.getElementById('login-logout');
const versionLabel = document.getElementById('login-version');
const donationBody = document.getElementById('login-donation-body');

/** Куда вернуться после входа: только локальный путь. */
function nextTarget() {
  const raw = new URLSearchParams(window.location.search).get('next') || '/';
  if (!raw.startsWith('/') || raw.startsWith('//')) return '/';
  return raw;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = '';
}

function setBusy(busy) {
  submit.disabled = busy;
  submit.textContent = busy ? 'Проверяем…' : 'Войти';
}

async function loadVersion() {
  try {
    const response = await fetch('/api/health', { headers: { Accept: 'application/json' } });
    if (!response.ok) return;
    const health = await response.json();
    const version = typeof health.version === 'string' ? health.version : '';
    versionLabel.textContent = version ? `локальный шлюз · v${version}` : 'локальный шлюз';
  } catch {
    // Версия — необязательная деталь.
  }
}

async function loadDonation() {
  try {
    const response = await fetch('/api/donation', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('нет данных');
    const config = await response.json();
    const links = Array.isArray(config?.links) ? config.links : [];
    const author = typeof config?.author === 'string' && config.author ? config.author : '';
    donationBody.replaceChildren();

    if (author) {
      const line = document.createElement('div');
      line.textContent = author;
      donationBody.append(line);
    }

    let rendered = 0;
    for (const link of links) {
      const row = document.createElement('div');
      if (typeof link?.url === 'string' && /^https?:\/\//i.test(link.url)) {
        const anchor = document.createElement('a');
        anchor.href = link.url;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = String(link.label ?? link.url);
        row.append(anchor);
        rendered += 1;
      } else if (typeof link?.value === 'string' && link.value) {
        const code = document.createElement('code');
        code.textContent = `${link.label ? link.label + ': ' : ''}${link.value}`;
        row.append(code);
        rendered += 1;
      }
      if (row.childElementCount) donationBody.append(row);
    }

    if (!rendered && !author) {
      const empty = document.createElement('div');
      empty.className = 'login-donation__empty';
      empty.textContent = 'Реквизиты поддержки не настроены в config/donation.json.';
      donationBody.append(empty);
    }
  } catch {
    donationBody.replaceChildren();
    const empty = document.createElement('div');
    empty.className = 'login-donation__empty';
    empty.textContent = 'Реквизиты поддержки недоступны.';
    donationBody.append(empty);
  }
}

function showAuthenticated(next) {
  title.textContent = 'Вы уже вошли';
  note.textContent = 'Сессия активна. Можно открыть панель или выйти и войти другим паролем.';
  form.hidden = true;
  actions.hidden = false;
  continueLink.href = next;
  clearError();
}

function showForm(message = '') {
  form.hidden = false;
  actions.hidden = true;
  if (message) showError(message);
  input.focus();
}

async function logout() {
  clearError();
  logoutButton.disabled = true;
  try {
    await fetch('/api/auth/logout', { method: 'POST', body: '{}', headers: { 'Content-Type': 'application/json' } });
    window.location.replace('/login.html');
  } catch {
    showError('Не удалось выйти: нет связи со шлюзом.');
  } finally {
    logoutButton.disabled = false;
  }
}

async function onSubmit(event) {
  event.preventDefault();
  clearError();
  const password = input.value;
  if (password.length < 6) {
    showError('Пароль должен быть не короче 6 символов.');
    input.focus();
    return;
  }

  setBusy(true);
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const payload = await response.json().catch(() => ({}));

    if (response.ok) {
      input.value = '';
      window.location.replace(nextTarget());
      return;
    }
    if (response.status === 429) {
      const seconds = Number(payload?.retryAfter) || 60;
      showError(`Слишком много неверных попыток. Попробуйте через ${seconds} с.`);
    } else if (response.status === 401) {
      showError('Неверный пароль.');
    } else {
      showError(payload?.error ?? `Шлюз ответил ошибкой ${response.status}.`);
    }
    input.select();
  } catch {
    showError('Не удалось связаться со шлюзом. Проверьте, что он запущен.');
  } finally {
    setBusy(false);
  }
}

async function boot() {
  await Promise.all([loadVersion(), loadDonation()]);

  const next = nextTarget();
  const params = new URLSearchParams(window.location.search);
  if (params.get('error') === 'pair') {
    showForm('QR-код устарел или уже использован. Введите пароль вручную.');
    return;
  }

  try {
    const response = await fetch('/api/auth/status', { headers: { Accept: 'application/json' } });
    const status = await response.json();
    if (!status?.required) {
      window.location.replace(next);
      return;
    }
    if (status.authenticated) {
      showAuthenticated(next);
      return;
    }
    showForm();
  } catch {
    showForm('Не удалось проверить статус входа. Обновите страницу.');
  }
}

form.addEventListener('submit', onSubmit);
reveal.addEventListener('click', () => {
  const visible = input.type === 'text';
  input.type = visible ? 'password' : 'text';
  reveal.textContent = visible ? 'показать' : 'скрыть';
  reveal.setAttribute('aria-pressed', String(!visible));
  input.focus();
});
logoutButton.addEventListener('click', logout);

boot();

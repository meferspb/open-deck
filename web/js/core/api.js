/**
 * Клиент REST API шлюза. Один порт, относительные URL, без внешних библиотек.
 */

const REQUEST_TIMEOUT_MS = 6000;

export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {{status?: number, code?: string}} [info]
   */
  constructor(message, { status = 0, code = 'request_failed' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

/**
 * @param {string} path
 * @param {{method?: string, body?: unknown}} [options]
 */
async function request(path, { method = 'GET', body } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(path, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
      cache: 'no-store',
    });

    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        throw new ApiError('Шлюз вернул ответ не в формате JSON', { status: response.status });
      }
    }

    if (!response.ok) {
      throw new ApiError(data?.error ?? `HTTP ${response.status}`, {
        status: response.status,
        code: data?.code ?? 'http_error',
      });
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error?.name === 'AbortError') {
      throw new ApiError('Шлюз не ответил вовремя', { code: 'timeout' });
    }
    throw new ApiError(error?.message ?? 'Сеть недоступна', { code: 'network' });
  } finally {
    clearTimeout(timer);
  }
}

export const api = {
  health: () => request('/api/health'),
  integrity: () => request('/api/integrity'),
  donation: () => request('/api/donation'),
  listProfiles: () => request('/api/profiles'),
  getProfile: (id) => request(`/api/profiles/${encodeURIComponent(id)}`),
  saveProfile: (profile) =>
    request(`/api/profiles/${encodeURIComponent(profile.id)}`, { method: 'PUT', body: profile }),
  telemetryVariables: () => request('/api/telemetry/variables'),
  telemetry: () => request('/api/telemetry'),
  selectAircraft: (profileId) =>
    request('/api/sim/aircraft', { method: 'POST', body: { profileId } }),
  sendCommand: (key, value) =>
    request('/api/sim/command', { method: 'POST', body: { key, value } }),
};

export function wsUrl() {
  const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${scheme}//${window.location.host}/ws`;
}

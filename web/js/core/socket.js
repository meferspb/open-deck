/**
 * WebSocket-клиент телеметрии: переподключение с backoff, keep-alive,
 * подтверждения команд по id.
 */

const RECONNECT_BASE_MS = 500;
const RECONNECT_MAX_MS = 8000;
const COMMAND_TIMEOUT_MS = 4000;
const PING_INTERVAL_MS = 20000;

/**
 * @param {{
 *   url: string,
 *   onMessage?: (message: any) => void,
 *   onStatus?: (event: {state: 'connecting'|'online'|'reconnecting'|'offline', detail?: string}) => void,
 * }} options
 */
export function createTelemetrySocket({ url, onMessage, onStatus }) {
  /** @type {WebSocket | null} */
  let socket = null;
  let attempt = 0;
  let stopped = false;
  /** @type {ReturnType<typeof setTimeout> | null} */
  let reconnectTimer = null;
  /** @type {ReturnType<typeof setInterval> | null} */
  let pingTimer = null;
  let latencyMs = null;
  let commandSeq = 0;

  /** @type {Map<string, {resolve: (v: any) => void, reject: (e: Error) => void, timer: ReturnType<typeof setTimeout>}>} */
  const pending = new Map();

  const setStatus = (state, detail) => onStatus?.({ state, detail });

  /**
   * @param {Record<string, unknown>} payload
   * @returns {boolean}
   */
  function sendRaw(payload) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(payload));
    return true;
  }

  function rejectPending(error) {
    for (const [, entry] of pending) {
      clearTimeout(entry.timer);
      entry.reject(error);
    }
    pending.clear();
  }

  function startPing() {
    stopPing();
    pingTimer = setInterval(() => {
      sendRaw({ type: 'ping', t: performance.now() });
    }, PING_INTERVAL_MS);
  }

  function stopPing() {
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = null;
  }

  function scheduleReconnect() {
    if (stopped) return;
    setStatus('offline', 'нет связи со шлюзом');
    attempt += 1;
    const delay = Math.min(RECONNECT_MAX_MS, RECONNECT_BASE_MS * 2 ** Math.min(attempt - 1, 5));
    const jitter = Math.random() * 250;
    reconnectTimer = setTimeout(connect, delay + jitter);
  }

  function handleMessage(event) {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch {
      return;
    }
    if (!message || typeof message !== 'object') return;

    if (message.type === 'pong') {
      if (typeof message.t === 'number') latencyMs = Math.max(0, Math.round(performance.now() - message.t));
      return;
    }

    if (message.type === 'ack') {
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      clearTimeout(entry.timer);
      if (message.ok) {
        entry.resolve(message);
      } else {
        const error = new Error(message.error ?? 'Команда отклонена');
        error.code = message.code ?? 'rejected';
        entry.reject(error);
      }
      return;
    }

    onMessage?.(message);
  }

  function connect() {
    if (stopped) return;
    setStatus(attempt === 0 ? 'connecting' : 'reconnecting');

    socket = new WebSocket(url);
    socket.addEventListener('open', () => {
      attempt = 0;
      setStatus('online');
      startPing();
    });
    socket.addEventListener('message', handleMessage);
    socket.addEventListener('close', () => {
      stopPing();
      socket = null;
      rejectPending(new Error('Соединение с шлюзом закрыто'));
      scheduleReconnect();
    });
    socket.addEventListener('error', () => {
      // Подробности недоступны по соображениям безопасности браузера;
      // следом придёт close и запустит переподключение.
    });
  }

  /**
   * Отправляет команду и ждёт подтверждения от шлюза.
   * @param {string} key
   * @param {unknown} value
   * @returns {Promise<{ok: boolean, value?: unknown}>}
   */
  function command(key, value) {
    const id = `c${(commandSeq += 1)}`;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error('Шлюз не подтвердил команду'));
      }, COMMAND_TIMEOUT_MS);

      pending.set(id, { resolve, reject, timer });
      if (!sendRaw({ type: 'command', id, key, value })) {
        pending.delete(id);
        clearTimeout(timer);
        reject(new Error('Нет соединения с шлюзом'));
      }
    });
  }

  function stop() {
    stopped = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    reconnectTimer = null;
    stopPing();
    rejectPending(new Error('Клиент остановлен'));
    socket?.close();
    socket = null;
  }

  connect();

  return {
    command,
    stop,
    get connected() {
      return socket?.readyState === WebSocket.OPEN;
    },
    get latencyMs() {
      return latencyMs;
    },
  };
}

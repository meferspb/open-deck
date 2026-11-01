/**
 * Крошечное хранилище состояния с подпиской.
 * Без фреймворка: приложение маленькое, а предсказуемость важнее магии.
 */

/**
 * @template T
 * @param {Partial<T>} [initialState]
 */
export function createStore(initialState = {}) {
  /** @type {Partial<T>} */
  let state = { ...initialState };
  /** @type {Set<(state: Partial<T>) => void>} */
  const listeners = new Set();

  return {
    /** @returns {Partial<T>} */
    get() {
      return state;
    },

    /**
     * Поверхностное обновление: вложенные объекты заменяются целиком.
     * @param {Partial<T>} patch
     */
    set(patch) {
      state = { ...state, ...patch };
      for (const listener of listeners) {
        try {
          listener(state);
        } catch (error) {
          console.error('store listener failed', error);
        }
      }
    },

    /**
     * @param {(state: Partial<T>) => void} listener
     * @returns {() => void} отписка
     */
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

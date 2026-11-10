"""Провайдер телеметрии MSFS через SimConnect (Windows, ctypes).

SimConnect не требует SDK при импорте: DLL загружается по требованию,
поэтому шлюз запускается и без симулятора (режим mock).

Что умеет:
  * открывает соединение с MSFS 2020/2024 и переподключается после
    перезапуска симулятора;
  * подписывается на все числовые SimVar из `telemetry.VARIABLES`, а также
    на строковые TITLE и ATC MODEL для автоопределения борта;
  * отправляет команды событиями SimConnect, а LVAR/RPN — через WASM-мост
    (Client Data Area);
  * если стандартный конфиг SimConnect не работает, пробует TCP
    `127.0.0.1:19999` через временный SimConnect.cfg (см. `_connect`).
"""

from __future__ import annotations

import ctypes
import glob
import logging
import os
import queue
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .. import telemetry
from ..settings import PACKAGE_DIR, REPO_ROOT
from .base import SimCommandError, SimProvider
from .client_data import ClientDataChannel

logger = logging.getLogger("msfs_gateway.simconnect")

#: SimConnect ищет SimConnect.cfg в текущем каталоге, поэтому на время
#: генерации временного cfg приходится менять CWD. Блокировка не даёт двум
#: потокам делать это одновременно; все остальные пути в приложении абсолютные.
_CWD_LOCK = threading.Lock()

# --- Константы из SimConnect.h ----------------------------------------
SIMCONNECT_DATATYPE_FLOAT64 = 4
#: Строки читаются отдельными определениями: заголовок борта и модель ATC.
SIMCONNECT_DATATYPE_STRING256 = 9
SIMCONNECT_PERIOD_VISUAL_FRAME = 2
SIMCONNECT_OBJECT_ID_USER = 0
# SIMCONNECT_RECV_ID: NULL=0, EXCEPTION=1, OPEN=2, QUIT=3, EVENT=4, …
SIMCONNECT_RECV_ID_EXCEPTION = 1
SIMCONNECT_RECV_ID_OPEN = 2
SIMCONNECT_RECV_ID_QUIT = 3
SIMCONNECT_RECV_ID_SIMOBJECT_DATA = 8
#: Client Data Area. Значение сверено с порядком enum в MSFS SDK; если
#: конкретная версия SimConnect его изменит, LVAR просто перестанут
#: приходить (таймаут), телеметрия SimVar продолжит работать.
SIMCONNECT_RECV_ID_CLIENT_DATA = 16
# SIMCONNECT_CLIENT_DATA_PERIOD / FLAGS
SIMCONNECT_CLIENT_DATA_PERIOD_ONCE = 1
SIMCONNECT_CLIENT_DATA_REQUEST_FLAG_DEFAULT = 0
SIMCONNECT_CLIENT_DATA_SET_FLAG_DEFAULT = 0
SIMCONNECT_GROUP_PRIORITY_HIGHEST = 1
SIMCONNECT_EVENT_FLAG_GROUPID_IS_PRIORITY = 0x00000010
S_OK = 0

_REQUEST_ID = 1
_DEFINE_ID = 1
#: Отдельные определения для строковых датумов (TITLE / ATC MODEL).
_TITLE_REQUEST_ID = 2
_TITLE_DEFINE_ID = 2
_ATC_REQUEST_ID = 3
_ATC_DEFINE_ID = 3

_DLL_CANDIDATES = (
    "SimConnect.dll",
    str(REPO_ROOT / "SimConnect.dll"),
    str(PACKAGE_DIR / "SimConnect.dll"),
    r"C:\Program Files\Microsoft Games\Microsoft Flight Simulator 2020\SimConnect.dll",
    r"C:\Program Files (x86)\Steam\steamapps\common\MicrosoftFlightSimulator\SimConnect.dll",
)

_DLL_GLOBS = (
    r"C:\Program Files\WindowsApps\Microsoft.FlightSimulator_*\SimConnect.dll",
    r"C:\Program Files\WindowsApps\Microsoft.Limitless_*\SimConnect.dll",
    r"C:\Program Files (x86)\Steam\steamapps\common\MicrosoftFlightSimulator\SimConnect.dll",
    r"C:\Program Files\Microsoft Games\Microsoft Flight Simulator 2024\SimConnect.dll",
)

_EXCEPTION_NAMES = {
    1: "ERROR",
    2: "SIZE_MISMATCH",
    3: "UNRECOGNIZED_ID",
    4: "UNOPENED",
    5: "VERSION_MISMATCH",
    6: "TOO_MANY_REQUESTS",
    7: "NAME_UNRECOGNIZED",
    8: "TOO_MANY_DEFINITIONS",
    9: "TOO_MANY_DEFINITIONS",
    10: "TOO_MANY_REQUESTS",
    11: "TOO_MANY_EVENTS",
    12: "TOO_MANY_DATA_REQUESTS",
}


class SimConnectError(RuntimeError):
    """SimConnect недоступен или вернул ошибку."""


def decode_string(raw: bytes) -> str:
    """Декодирует строковый датум SimConnect (буфер с NUL, UTF-8/ANSI)."""
    text = raw.split(b"\x00", 1)[0]
    for encoding in ("utf-8", "cp1251"):
        try:
            return text.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return text.decode("latin-1", "replace").strip()


class _Recv(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_uint32),
        ("dwVersion", ctypes.c_uint32),
        ("dwID", ctypes.c_uint32),
    ]


class _RecvSimObjectData(ctypes.Structure):
    #: Порядок полей — строго по SimConnect.h:
    #: dwRequestID, dwObjectID, dwDefineID, dwFlags, dwEntryNumber, dwOutOf,
    #: dwDefineCount. ctypes-структура должна совпадать с SDK побайтно.
    _fields_ = [
        *_Recv._fields_,
        ("dwRequestID", ctypes.c_uint32),
        ("dwObjectID", ctypes.c_uint32),
        ("dwDefineID", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("dwEntryNumber", ctypes.c_uint32),
        ("dwOutOf", ctypes.c_uint32),
        ("dwDefineCount", ctypes.c_uint32),
    ]


class _RecvException(ctypes.Structure):
    _fields_ = [
        *_Recv._fields_,
        ("dwException", ctypes.c_uint32),
        ("dwSendID", ctypes.c_uint32),
        ("dwIndex", ctypes.c_uint32),
    ]


_DATA_OFFSET = ctypes.sizeof(_RecvSimObjectData)

if hasattr(ctypes, "WINFUNCTYPE"):  # только Windows
    DispatchProc = ctypes.WINFUNCTYPE(None, ctypes.POINTER(_Recv), ctypes.c_uint32, ctypes.c_void_p)
else:  # pragma: no cover - упрощает импорт на не-Windows
    DispatchProc = None  # type: ignore[assignment]


def _load_simconnect_dll(explicit: Path | None) -> Any:
    """Ищет и загружает SimConnect.dll, не полагаясь на переменную PATH."""
    if not hasattr(ctypes, "WinDLL"):
        raise SimConnectError("SimConnect доступен только на Windows")

    candidates: list[str] = []
    if explicit is not None:
        candidates.append(str(explicit))
    env_path = os.environ.get("MSFS_SIMCONNECT_DLL")
    if env_path:
        candidates.append(env_path)
    candidates.extend(_DLL_CANDIDATES)

    for pattern in _DLL_GLOBS:
        try:
            candidates.extend(sorted(glob.glob(pattern))[:1])
        except OSError:  # pragma: no cover - недоступный каталог
            continue

    errors: list[str] = []
    for candidate in candidates:
        if candidate == "SimConnect.dll":
            # Дать шанс стандартному поиску Windows (каталог приложения, System32).
            try:
                return ctypes.WinDLL(candidate)  # type: ignore[attr-defined]
            except OSError as exc:
                errors.append(f"{candidate}: {exc}")
                continue
        path = Path(candidate)
        if not path.is_file():
            continue
        try:
            return ctypes.WinDLL(str(path))  # type: ignore[attr-defined]
        except OSError as exc:
            errors.append(f"{path}: {exc}")

    detail = "; ".join(errors) if errors else "файл не найден"
    raise SimConnectError(
        "Не удалось загрузить SimConnect.dll. Скопируйте его из MSFS SDK "
        f"(SimConnect SDK\\lib) в каталог шлюза или укажите --simconnect-dll. Детали: {detail}"
    )


class SimConnectSim(SimProvider):
    """Читает телеметрию из MSFS и отправляет команды событиями."""

    name = "simconnect"

    def __init__(
        self,
        dll_path: Path | None = None,
        *,
        host: str = "127.0.0.1",
        port: int = 19999,
    ) -> None:
        if DispatchProc is None:
            raise SimConnectError("SimConnect поддерживается только на Windows")
        self._dll_path = dll_path
        self._host = host
        self._port = port
        self._dll: Any = None
        self._handle: Any = None
        self._lock = threading.RLock()
        self._values: dict[str, Any] = telemetry.empty_snapshot()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._dispatch_proc = DispatchProc(self._on_dispatch)  # держим ссылку
        self._opened_at = 0.0
        self._last_data_at = 0.0
        self._last_numeric_at = 0.0
        self._quit = threading.Event()
        self._event_ids: dict[str, int] = {}

        # Client Data Area: запросы выполняются в потоке диспетчеризации,
        # потому что SimConnect не рассчитан на многопоточные вызовы.
        self._dispatch_queue: queue.SimpleQueue[
            tuple[Callable[[], None], threading.Event | None, list[BaseException]]
        ] = queue.SimpleQueue()
        self._dispatch_thread_id: int | None = None
        self._client_sink: Callable[[int, bytes], None] | None = None
        self._wasm: Any = None

        #: Датумы, реально принятые SimConnect, в порядке datum_id.
        #: Заполняется в `_open()` после успешных `AddToDataDefinition`.
        self._data_keys: list[str] = []
        self._diagnostics: deque[dict[str, Any]] = deque(maxlen=48)

        self._connect()

    # ------------------------------------------------------------------
    # Соединение
    # ------------------------------------------------------------------
    @property
    def connected(self) -> bool:
        if self._handle is None:
            return False
        if self._last_data_at:
            return (time.monotonic() - self._last_data_at) < 3.0
        # Сразу после открытия данные ещё не пришли — даём симулятору время.
        return (time.monotonic() - self._opened_at) < 10.0

    def _bind(self) -> None:
        """Описывает сигнатуры — ctypes без argtypes легко портит стек."""
        dll = self._dll
        dll.SimConnect_Open.restype = ctypes.c_long
        dll.SimConnect_Open.argtypes = [
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.c_char_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
        ]
        dll.SimConnect_Close.restype = ctypes.c_long
        dll.SimConnect_Close.argtypes = [ctypes.c_void_p]

        dll.SimConnect_AddToDataDefinition.restype = ctypes.c_long
        dll.SimConnect_AddToDataDefinition.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_float,
            ctypes.c_uint32,
        ]
        dll.SimConnect_RequestDataOnSimObject.restype = ctypes.c_long
        dll.SimConnect_RequestDataOnSimObject.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        dll.SimConnect_CallDispatch.restype = ctypes.c_long
        dll.SimConnect_CallDispatch.argtypes = [ctypes.c_void_p, DispatchProc, ctypes.c_void_p]

        dll.SimConnect_MapClientEventToSimEvent.restype = ctypes.c_long
        dll.SimConnect_MapClientEventToSimEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
        ]
        dll.SimConnect_TransmitClientEvent.restype = ctypes.c_long
        dll.SimConnect_TransmitClientEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]

        # --- Client Data Area (WASM-мост: LVAR/RPN) -------------------
        dll.SimConnect_MapClientDataNameToID.restype = ctypes.c_long
        dll.SimConnect_MapClientDataNameToID.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_uint32,
        ]
        dll.SimConnect_AddToClientDataDefinition.restype = ctypes.c_long
        dll.SimConnect_AddToClientDataDefinition.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_float,
            ctypes.c_uint32,
        ]
        dll.SimConnect_RequestClientData.restype = ctypes.c_long
        dll.SimConnect_RequestClientData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]
        dll.SimConnect_SetClientData.restype = ctypes.c_long
        dll.SimConnect_SetClientData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]

    def _connect(self) -> None:
        self._dll = _load_simconnect_dll(self._dll_path)
        self._bind()

        try:
            self._open()
            return
        except SimConnectError as first_error:
            # Стандартный конфиг SimConnect (SimConnect.cfg в профиле или
            # рядом с exe) может указывать на несуществующий канал. MSFS
            # 2020/2024 по умолчанию слушает TCP 19999 — пробуем его через
            # временный cfg, не трогая файлы пользователя.
            logger.warning(
                "SimConnect не открылся (%s); пробую TCP %s:%d",
                first_error,
                self._host,
                self._port,
            )
            try:
                if self._open_via_generated_config():
                    return
            except SimConnectError as second_error:
                raise SimConnectError(
                    f"{first_error}; TCP {self._host}:{self._port}: {second_error}"
                ) from second_error
            raise SimConnectError(
                f"{first_error}; TCP {self._host}:{self._port} тоже недоступен"
            ) from first_error

    def _open_via_generated_config(self) -> bool:
        """Открывает соединение по TCP, подсунув SimConnect временный cfg.

        Клиент SimConnect ищет `SimConnect.cfg` в текущем каталоге, поэтому
        на время вызова переходим во временную папку и возвращаемся обратно.
        """
        config = (
            "[SimConnect]\n"
            "Protocol=IPv4\n"
            f"Address={self._host}\n"
            f"Port={self._port}\n"
            "MaxClients=64\n"
            "MaxRecvData=8192\n"
            "MaxSendData=8192\n"
        )
        with tempfile.TemporaryDirectory(prefix="open-deck-simconnect-") as tmp:
            Path(tmp, "SimConnect.cfg").write_text(config, encoding="ascii")
            with _CWD_LOCK:
                previous = os.getcwd()
                try:
                    os.chdir(tmp)
                    self._open()
                    logger.info("SimConnect подключён через TCP %s:%d", self._host, self._port)
                    return True
                except SimConnectError as exc:
                    logger.debug("TCP %s:%d не помог: %s", self._host, self._port, exc)
                    return False
                finally:
                    os.chdir(previous)

    def _open(self) -> None:
        handle = ctypes.c_void_p()
        result = self._dll.SimConnect_Open(
            ctypes.byref(handle), b"Open Deck for MSFS", None, 0, None, 0
        )
        if result != S_OK or not handle.value:
            raise SimConnectError(f"SimConnect_Open завершился с кодом 0x{result & 0xFFFFFFFF:08X}")

        self._handle = handle
        self._opened_at = time.monotonic()
        self._quit.clear()

        # Собираем определение только из датумов, которые SimConnect принял:
        # иначе при отказе одной переменной индексы последующих значений
        # сместились бы и панель показывала бы чужие величины.
        self._data_keys = []
        for key, variable in telemetry.VARIABLES.items():
            sim_var = variable.sim_var
            if not sim_var or variable.kind not in {"number", "bool"}:
                continue
            datum_id = len(self._data_keys)
            units = (variable.sim_unit or "number").encode("utf-8")
            hr = self._dll.SimConnect_AddToDataDefinition(
                self._handle,
                _DEFINE_ID,
                sim_var.encode("utf-8"),
                units,
                SIMCONNECT_DATATYPE_FLOAT64,
                0.0,
                datum_id,
            )
            if hr != S_OK:
                logger.warning(
                    "AddToDataDefinition(%s) вернул 0x%08X — переменная будет недоступна",
                    sim_var,
                    hr & 0xFFFFFFFF,
                )
                self._record_diagnostic(
                    "definition_failed", simVar=sim_var, hresult=hr & 0xFFFFFFFF
                )
                continue
            self._data_keys.append(key)

        hr = self._dll.SimConnect_RequestDataOnSimObject(
            self._handle,
            _REQUEST_ID,
            _DEFINE_ID,
            SIMCONNECT_OBJECT_ID_USER,
            SIMCONNECT_PERIOD_VISUAL_FRAME,
            0,
            0,
            0,
            0,
        )
        if hr != S_OK:
            self._disconnect()
            raise SimConnectError(f"RequestDataOnSimObject вернул 0x{hr & 0xFFFFFFFF:08X}")

        self._request_identity()

        logger.info("SimConnect подключён (датчиков: %d)", len(self._data_keys))

    def _request_identity(self) -> None:
        """Подписка на TITLE и ATC MODEL для автоопределения профиля.

        Строковые датумы нельзя смешивать с числами в одном определении,
        поэтому это отдельные определения и запросы. Их отсутствие не
        критично: телеметрия продолжит работать, автоопределение — нет.
        """
        for define_id, request_id, name, label in (
            (_TITLE_DEFINE_ID, _TITLE_REQUEST_ID, b"TITLE", "TITLE"),
            (_ATC_DEFINE_ID, _ATC_REQUEST_ID, b"ATC MODEL", "ATC MODEL"),
        ):
            hr = self._dll.SimConnect_AddToDataDefinition(
                self._handle,
                define_id,
                name,
                None,
                SIMCONNECT_DATATYPE_STRING256,
                0.0,
                0,
            )
            if hr != S_OK:
                logger.warning(
                    "AddToDataDefinition(%s) вернул 0x%08X — автоопределение борта ограничено",
                    label,
                    hr & 0xFFFFFFFF,
                )
                self._record_diagnostic(
                    "identity_definition_failed", label=label, hresult=hr & 0xFFFFFFFF
                )
                continue
            hr = self._dll.SimConnect_RequestDataOnSimObject(
                self._handle,
                request_id,
                define_id,
                SIMCONNECT_OBJECT_ID_USER,
                SIMCONNECT_PERIOD_VISUAL_FRAME,
                0,
                0,
                0,
                0,
            )
            if hr != S_OK:
                logger.warning("RequestDataOnSimObject(%s) вернул 0x%08X", label, hr & 0xFFFFFFFF)
                self._record_diagnostic("request_failed", label=label, hresult=hr & 0xFFFFFFFF)

    def _record_diagnostic(self, event: str, **details: Any) -> None:
        entry = {"ts": round(time.time(), 3), "event": event, **details}
        with self._lock:
            self._diagnostics.append(entry)
        logger.debug("SimConnect diagnostic: %s", entry)

    def diagnostics(self) -> list[dict[str, Any]]:
        """Последние события SimConnect для /api/diagnostics."""
        with self._lock:
            return list(self._diagnostics)

    def _disconnect(self) -> None:
        if self._dll is not None and self._handle is not None:
            try:
                self._dll.SimConnect_Close(self._handle)
            except Exception:
                logger.debug("Ошибка при закрытии SimConnect", exc_info=True)
        self._handle = None
        self._last_data_at = 0.0
        self._last_numeric_at = 0.0
        # Event ID привязаны к соединению: после перезапуска MSFS их нужно
        # маппить заново, иначе команды уйдут в никуда.
        with self._lock:
            self._event_ids.clear()

        # Все ожидающие запросы Client Data относятся к старому соединению.
        transport = getattr(self._wasm, "transport", None) if self._wasm is not None else None
        close = getattr(transport, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logger.debug("Ошибка при сбросе WASM-транспорта", exc_info=True)

    # ------------------------------------------------------------------
    # Жизненный цикл
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Запускает поток диспетчеризации/переподключения."""
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="simconnect", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Останавливает поток и закрывает соединение."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning("Поток SimConnect не завершился за 5 с")
        self._disconnect()

    def _run(self) -> None:
        self._dispatch_thread_id = threading.get_ident()
        try:
            while not self._stop.is_set():
                if self._handle is None:
                    try:
                        self._connect()
                    except Exception as exc:
                        # OSError при создании временного cfg/смене каталога
                        # тоже не должен убивать поток переподключения.
                        logger.warning("Переподключение к MSFS не удалось: %s", exc)
                        self._stop.wait(5.0)
                        continue
                try:
                    self._dll.SimConnect_CallDispatch(self._handle, self._dispatch_proc, None)
                except Exception:
                    logger.exception("Сбой SimConnect_CallDispatch")
                    self._stop.wait(1.0)

                # Запросы Client Data выполняем здесь: SimConnect не любит
                # вызовы из чужих потоков.
                self._drain_dispatch_queue()

                if self._quit.is_set():
                    logger.warning("MSFS закрыл соединение, переподключаюсь")
                    self._disconnect()
                    self._stop.wait(2.0)
                time.sleep(0.005)
        finally:
            self._dispatch_thread_id = None
            # Не оставляем вызывающих ждать мёртвый поток.
            self._fail_dispatch_queue("поток SimConnect остановлен")

    # ------------------------------------------------------------------
    # Очередь вызовов в поток диспетчеризации
    # ------------------------------------------------------------------
    def run_on_dispatch(
        self,
        callback: Callable[[], None],
        *,
        wait: bool = True,
        timeout: float = 5.0,
    ) -> None:
        """Выполнить вызов SimConnect в его собственном потоке.

        Из потока диспетчеризации (например, из колбэка) вызов выполняется
        сразу — иначе получился бы самоблокирующийся запрос.
        """
        if self._handle is None:
            raise SimConnectError("Нет соединения с MSFS")
        if threading.get_ident() == self._dispatch_thread_id:
            callback()
            return

        done = threading.Event() if wait else None
        errors: list[BaseException] = []
        self._dispatch_queue.put((callback, done, errors))
        if done is None:
            return
        if not done.wait(timeout):
            raise SimConnectError("SimConnect не обработал запрос вовремя")
        if errors:
            raise errors[0]

    def _drain_dispatch_queue(self) -> None:
        while True:
            try:
                callback, done, errors = self._dispatch_queue.get_nowait()
            except queue.Empty:
                return
            try:
                callback()
            except BaseException as exc:
                errors.append(exc)
            finally:
                if done is not None:
                    done.set()

    def _fail_dispatch_queue(self, reason: str) -> None:
        while True:
            try:
                _callback, done, errors = self._dispatch_queue.get_nowait()
            except queue.Empty:
                return
            errors.append(SimConnectError(reason))
            if done is not None:
                done.set()

    def set_client_data_sink(self, sink: Callable[[int, bytes], None] | None) -> None:
        """Куда отдавать ответы Client Data (request_id, payload)."""
        self._client_sink = sink

    def wasm_bridge(self) -> Any:
        """Ленивый WASM-мост поверх Client Data Area (LVAR/RPN)."""
        with self._lock:
            if self._wasm is None:
                from .wasm_bridge import WasmBridge

                self._wasm = WasmBridge(SimConnectWasmTransport(self), logger=logger)
            return self._wasm

    # ------------------------------------------------------------------
    # Обработка сообщений SimConnect
    # ------------------------------------------------------------------
    def _on_dispatch(self, data_ptr: Any, cb_data: int, context: Any) -> None:
        # Исключение внутри колбэка уронило бы нативное приложение.
        try:
            self._handle_message(data_ptr, cb_data)
        except Exception as exc:
            self._record_diagnostic("dispatch_error", error=str(exc))
            logger.exception("Ошибка обработки сообщения SimConnect")

    def _handle_message(self, data_ptr: Any, cb_data: int) -> None:
        recv = data_ptr.contents
        if recv.dwID == SIMCONNECT_RECV_ID_SIMOBJECT_DATA:
            self._handle_data(data_ptr, cb_data)
        elif recv.dwID == SIMCONNECT_RECV_ID_CLIENT_DATA:
            self._handle_client_data(data_ptr, cb_data)
        elif recv.dwID == SIMCONNECT_RECV_ID_EXCEPTION:
            exception = ctypes.cast(data_ptr, ctypes.POINTER(_RecvException)).contents
            name = _EXCEPTION_NAMES.get(exception.dwException, "UNKNOWN")
            logger.warning(
                "SimConnect исключение %s (%d), sendId=%d, index=%d",
                name,
                exception.dwException,
                exception.dwSendID,
                exception.dwIndex,
            )
            self._record_diagnostic(
                "simconnect_exception",
                name=name,
                code=exception.dwException,
                sendId=exception.dwSendID,
                index=exception.dwIndex,
            )
        elif recv.dwID == SIMCONNECT_RECV_ID_QUIT:
            self._quit.set()

    def _handle_client_data(self, data_ptr: Any, cb_data: int) -> None:
        """Ответ Client Data Area: заголовок тот же, что у SIMOBJECT_DATA."""
        message = ctypes.cast(data_ptr, ctypes.POINTER(_RecvSimObjectData)).contents
        available = cb_data - _DATA_OFFSET
        if available <= 0:
            return
        payload = ctypes.string_at(ctypes.addressof(message) + _DATA_OFFSET, available)
        sink = self._client_sink
        if sink is not None:
            try:
                sink(int(message.dwRequestID), payload)
            except Exception:
                logger.exception("Ошибка обработки Client Data")

    def _handle_data(self, data_ptr: Any, cb_data: int) -> None:
        message = ctypes.cast(data_ptr, ctypes.POINTER(_RecvSimObjectData)).contents

        if message.dwDefineID == _TITLE_DEFINE_ID:
            self._store_string(message, cb_data, "aircraft.title")
            return
        if message.dwDefineID == _ATC_DEFINE_ID:
            self._store_string(message, cb_data, "aircraft.atcModel")
            return

        if message.dwDefineID != _DEFINE_ID or not message.dwDefineCount:
            return

        count = int(message.dwDefineCount)
        available = (cb_data - _DATA_OFFSET) // ctypes.sizeof(ctypes.c_double)
        count = max(0, min(count, available, len(self._data_keys)))
        if count == 0:
            return

        array_type = ctypes.c_double * count
        # Данные начинаются ПОСЛЕ заголовка SIMCONNECT_RECV_*: адрес структуры
        # указывает на её начало, а не на полезную нагрузку.
        array = array_type.from_address(ctypes.addressof(message) + _DATA_OFFSET)

        with self._lock:
            for index in range(count):
                key = self._data_keys[index]
                try:
                    self._values[key] = telemetry.coerce(key, array[index])
                except ValueError:
                    continue
            left = self._values.get("fuel.leftGal")
            right = self._values.get("fuel.rightGal")
            if isinstance(left, float) and isinstance(right, float):
                self._values["fuel.totalGal"] = left + right
        self._last_data_at = time.monotonic()
        self._last_numeric_at = self._last_data_at

    def _store_string(self, message: Any, cb_data: int, key: str) -> None:
        available = cb_data - _DATA_OFFSET
        if available <= 0:
            return
        raw = ctypes.string_at(ctypes.addressof(message) + _DATA_OFFSET, min(available, 260))
        text = decode_string(raw)
        if not text:
            return
        with self._lock:
            self._values[key] = text
        self._last_data_at = time.monotonic()

    # ------------------------------------------------------------------
    # Данные и команды
    # ------------------------------------------------------------------
    def read(self) -> dict[str, Any]:
        """Снимок значений.

        Переменные, которых нет в принятом определении SimConnect, и все
        числовые значения при отсутствии свежих данных помечаются `None`.
        Иначе потребитель (панель, ассистент) не отличит отказ SimVar от
        настоящего нуля.
        """
        with self._lock:
            values = dict(self._values)
            data_keys = set(self._data_keys)
            stale = self._last_numeric_at <= 0.0 or not self.connected
            for key, variable in telemetry.VARIABLES.items():
                # totalGal — вычисляемая переменная, её нет в SimConnect-определении.
                if key == "fuel.totalGal":
                    continue
                if variable.kind in {"number", "bool"}:
                    if key not in data_keys or stale:
                        values[key] = None
                elif variable.kind == "string" and stale:
                    values[key] = None
            if stale:
                values["aircraft.atcModel"] = None
            left = values.get("fuel.leftGal")
            right = values.get("fuel.rightGal")
            if stale or left is None or right is None:
                values["fuel.totalGal"] = None
            elif values.get("fuel.totalGal") is None:
                values["fuel.totalGal"] = round(float(left) + float(right), 3)

            # Радиовысотомер не является рабочим инструментом на эшелоне;
            # выше 2500 ft значение бесполезно для ассистента и вводит в
            # заблуждение, поэтому отдаём «нет данных».
            radio_alt = values.get("aircraft.radioAltitudeFt")
            if (
                isinstance(radio_alt, (int, float))
                and not isinstance(radio_alt, bool)
                and float(radio_alt) > 2500.0
            ):
                values["aircraft.radioAltitudeFt"] = None
            return values

    @property
    def aircraft_title(self) -> str | None:
        """Название борта из TITLE (только для живых данных)."""
        if not self.connected or self._last_data_at <= 0.0:
            return None
        title = self._values.get("aircraft.title")
        return title or None

    @property
    def atc_model(self) -> str | None:
        """Модель ATC (только для живых данных)."""
        if not self.connected or self._last_data_at <= 0.0:
            return None
        model = self._values.get("aircraft.atcModel")
        return model or None

    def apply_command(self, key: str, value: Any) -> None:
        """Применяет команду событием SimConnect."""
        variable = telemetry.get(key)
        if variable is None or not variable.writable or not variable.sim_event:
            raise SimCommandError(f"Переменная {key!r} не принимает команды")
        if self._handle is None or not self.connected:
            raise SimCommandError("Нет соединения с MSFS")

        target = telemetry.coerce(key, value)

        if variable.sim_event_param:
            if isinstance(target, bool):
                event_data = 1 if target else 0
            elif isinstance(target, (int, float)):
                scaled = float(target) * variable.sim_event_scale
                event_data = round(scaled) & 0xFFFFFFFF
            else:
                raise SimCommandError(f"{key}: событие {variable.sim_event} ожидает число")
        else:
            # Событие TOGGLE_* переключает состояние, поэтому «set» реализуем
            # сравнением с текущим значением и отправкой события только при различии.
            event_data = 0
            with self._lock:
                current = self._values.get(key)
            if isinstance(target, bool) and bool(current) == target:
                return

        event_name = variable.sim_event

        def transmit() -> None:
            # SimConnect не рассчитан на вызовы из разных потоков: команда
            # выполняется в потоке диспетчеризации, как и Client Data.
            event_id = self._event_id_for(key, event_name)
            result = self._dll.SimConnect_TransmitClientEvent(
                self._handle,
                SIMCONNECT_OBJECT_ID_USER,
                event_id,
                event_data,
                SIMCONNECT_GROUP_PRIORITY_HIGHEST,
                SIMCONNECT_EVENT_FLAG_GROUPID_IS_PRIORITY,
            )
            if result != S_OK:
                raise SimCommandError(
                    f"TransmitClientEvent({event_name}) вернул 0x{result & 0xFFFFFFFF:08X}"
                )

        try:
            self.run_on_dispatch(transmit)
        except SimConnectError as exc:
            raise SimCommandError(f"SimConnect не выполнил команду: {exc}") from exc

    def _event_id_for(self, key: str, event_name: str) -> int:
        with self._lock:
            event_id = self._event_ids.get(key)
            if event_id is not None:
                return event_id
            event_id = len(self._event_ids) + 1
            result = self._dll.SimConnect_MapClientEventToSimEvent(
                self._handle, event_id, event_name.encode("utf-8")
            )
            if result != S_OK:
                raise SimCommandError(
                    f"MapClientEventToSimEvent({event_name}) вернул 0x{result & 0xFFFFFFFF:08X}"
                )
            self._event_ids[key] = event_id
            return event_id


class SimConnectClientDataBackend:
    """Транспорт Client Data Area поверх конкретного соединения SimConnect.

    Идентификаторы областей и определений выделяются один раз на соединение;
    сами вызовы API выполняются в потоке диспетчеризации через
    [SimConnectSim.run_on_dispatch].
    """

    def __init__(self, sim: SimConnectSim) -> None:
        self._sim = sim
        self._lock = threading.RLock()
        self._area_ids: dict[str, int] = {}
        self._sizes: dict[str, int] = {}
        self._defines: dict[tuple[str, int], int] = {}
        self._next_area = 1
        self._next_define = 1
        self._sink: Callable[[int, bytes], None] | None = None
        sim.set_client_data_sink(self._on_payload)

    # --- канал ------------------------------------------------------
    def set_sink(self, sink: Callable[[int, bytes], None]) -> None:
        self._sink = sink

    def _on_payload(self, request_id: int, data: bytes) -> None:
        sink = self._sink
        if sink is not None:
            sink(request_id, data)

    def reset(self) -> None:
        """Новое соединение — старые ID областей недействительны."""
        with self._lock:
            self._area_ids.clear()
            self._sizes.clear()
            self._defines.clear()

    # --- геометрия --------------------------------------------------
    def ensure_area(self, name: str, size: int) -> None:
        if size <= 0:
            raise ValueError("Размер области Client Data должен быть больше нуля")

        with self._lock:
            area_id = self._area_ids.get(name)
            new_area = area_id is None
            if area_id is None:
                area_id = self._next_area
                self._next_area += 1
                self._area_ids[name] = area_id

            define_id = self._defines.get((name, size))
            new_define = define_id is None
            if define_id is None:
                define_id = self._next_define
                self._next_define += 1
                self._defines[(name, size)] = define_id
            self._sizes[name] = size

        def apply() -> None:
            dll = self._sim._dll
            handle = self._sim._handle
            if new_area:
                result = dll.SimConnect_MapClientDataNameToID(handle, name.encode("utf-8"), area_id)
                if result != S_OK:
                    raise SimConnectError(
                        f"MapClientDataNameToID({name}) вернул 0x{result & 0xFFFFFFFF:08X}"
                    )
            if new_define:
                result = dll.SimConnect_AddToClientDataDefinition(
                    handle, define_id, 0, size, 0.0, 0
                )
                if result != S_OK:
                    raise SimConnectError(
                        f"AddToClientDataDefinition({name}, {size}) "
                        f"вернул 0x{result & 0xFFFFFFFF:08X}"
                    )

        self._sim.run_on_dispatch(apply)

    def _ids_for(self, name: str) -> tuple[int, int]:
        with self._lock:
            area_id = self._area_ids.get(name)
            size = self._sizes.get(name)
            define_id = self._defines.get((name, size)) if size is not None else None
        if area_id is None or define_id is None:
            raise SimConnectError(f"Область Client Data не подготовлена: {name}")
        return area_id, define_id

    # --- операции ---------------------------------------------------
    def request_read(self, name: str, request_id: int) -> None:
        area_id, define_id = self._ids_for(name)

        def apply() -> None:
            dll = self._sim._dll
            result = dll.SimConnect_RequestClientData(
                self._sim._handle,
                area_id,
                request_id,
                define_id,
                SIMCONNECT_CLIENT_DATA_PERIOD_ONCE,
                SIMCONNECT_CLIENT_DATA_REQUEST_FLAG_DEFAULT,
                0,
                0,
                0,
            )
            if result != S_OK:
                raise SimConnectError(
                    f"RequestClientData({name}) вернул 0x{result & 0xFFFFFFFF:08X}"
                )

        # Ждать не нужно: ответ придёт в колбэк, канал ждёт его сам.
        self._sim.run_on_dispatch(apply, wait=False)

    def write_area(self, name: str, payload: bytes) -> None:
        area_id, define_id = self._ids_for(name)
        size = len(payload)
        buffer = ctypes.create_string_buffer(payload, size)

        def apply() -> None:
            dll = self._sim._dll
            result = dll.SimConnect_SetClientData(
                self._sim._handle,
                area_id,
                define_id,
                SIMCONNECT_CLIENT_DATA_SET_FLAG_DEFAULT,
                0,
                size,
                ctypes.cast(buffer, ctypes.c_void_p),
            )
            if result != S_OK:
                raise SimConnectError(f"SetClientData({name}) вернул 0x{result & 0xFFFFFFFF:08X}")

        self._sim.run_on_dispatch(apply)


class SimConnectWasmTransport:
    """`WasmTransport` (см. wasm_bridge) поверх Client Data Area."""

    def __init__(self, sim: SimConnectSim) -> None:
        self._sim = sim
        self.backend = SimConnectClientDataBackend(sim)
        self.channel = ClientDataChannel(self.backend, timeout=1.2, logger=logger)

    @property
    def available(self) -> bool:
        return self._sim.connected and self.channel.available

    def read_area(self, area: str, size: int) -> bytes | None:
        return self.channel.read_area(area, size)

    def write_area(self, area: str, payload: bytes) -> None:
        self.channel.write_area(area, payload)

    def close(self) -> None:
        """Сбросить ожидания и привязки к прежнему соединению."""
        self.channel.fail_all("соединение с MSFS закрыто")
        self.channel.reset()
        self.backend.reset()

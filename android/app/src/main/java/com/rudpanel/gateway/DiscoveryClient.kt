package com.rudpanel.gateway

import android.util.Log
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetSocketAddress
import java.net.SocketTimeoutException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Найденный в локальной сети хост.
 *
 * [key] уникален в пределах сессии; [lastSeenAt] нужен, чтобы убирать
 * хосты, которые перестали вещать.
 */
data class HostInfo(
    val name: String,
    val address: String,
    val port: Int,
    val version: String,
    val profileCount: Int,
    val lastSeenAt: Long = System.currentTimeMillis(),
) {
    val key: String get() = "$address:$port"
    val origin: String get() = "http://$address:$port"
}

/**
 * Приёмник UDP-биконов шлюза (порт 8761).
 *
 * Хост рассылает JSON вида:
 * `{"type":"rud-panel-gateway","name":"PC","version":"0.1.0","httpPort":8760,"profiles":[...]}`
 *
 * Работает в фоновом потоке; список хостов отдаётся через [onHosts],
 * ошибка привязки/приёма — через [onError]. После остановки или сбоя
 * поток завершается и снимает признак работы, поэтому [start] можно
 * вызвать повторно (например, после освобождения порта).
 */
class DiscoveryClient(
    private val port: Int = DEFAULT_PORT,
    private val onHosts: (List<HostInfo>) -> Unit,
    private val onError: (String) -> Unit = {},
) {

    private val running = AtomicBoolean(false)
    private val socketLock = Any()
    private val hostsLock = Any()

    private var thread: Thread? = null

    @Volatile
    private var socket: DatagramSocket? = null

    private val hosts = LinkedHashMap<String, HostInfo>()
    private var lastEmitAt = 0L

    fun snapshot(): List<HostInfo> = synchronized(hostsLock) {
        hosts.values.sortedBy { it.name.lowercase() }
    }

    fun start() {
        if (!running.compareAndSet(false, true)) return
        thread = Thread({ loop() }, "rud-discovery").apply {
            isDaemon = true
            start()
        }
    }

    fun stop() {
        running.set(false)
        synchronized(socketLock) {
            try {
                socket?.close()
            } catch (ignored: Exception) {
                // Сокет уже закрыт — это нормально при остановке.
            }
            socket = null
        }
        thread = null
        synchronized(hostsLock) { hosts.clear() }
    }

    private fun loop() {
        var failure: String? = null
        try {
            val sock = DatagramSocket(null).apply {
                reuseAddress = true
                bind(InetSocketAddress(port))
                soTimeout = RECEIVE_TIMEOUT_MS
            }
            synchronized(socketLock) {
                if (!running.get()) {
                    // stop() успел раньше, чем поток дошёл до bind: не течём сокетом.
                    sock.close()
                    return
                }
                socket = sock
            }

            val buffer = ByteArray(MAX_PACKET_BYTES)
            while (running.get()) {
                val packet = DatagramPacket(buffer, buffer.size)
                try {
                    sock.receive(packet)
                } catch (timeout: SocketTimeoutException) {
                    prune()
                    emitThrottled(force = true)
                    continue
                }

                if (handle(packet)) {
                    // Чистим «пропавшие» хосты на каждом пакете, а не только
                    // по таймауту: при потоке биконов таймаут может не наступить.
                    prune()
                    emitThrottled()
                }
            }
        } catch (error: Exception) {
            failure = error.message ?: error.javaClass.simpleName
            Log.w(TAG, "UDP-приёмник остановлен", error)
        } finally {
            running.set(false)
            synchronized(socketLock) {
                try {
                    socket?.close()
                } catch (ignored: Exception) {
                    // уже закрыт
                }
                socket = null
            }
            thread = null
            if (failure != null) {
                onError(failure)
            } else {
                emit()
            }
        }
    }

    private fun handle(packet: DatagramPacket): Boolean {
        val address = packet.address?.hostAddress ?: return false
        // IPv6-биконы пропускаем: шлюз вещает в IPv4, а WebView проще с IPv4.
        if (address.contains(':')) return false

        val payload = try {
            JSONObject(String(packet.data, packet.offset, packet.length, Charsets.UTF_8))
        } catch (error: Exception) {
            return false
        }
        if (payload.optString("type") != BEACON_TYPE) return false

        val httpPort = payload.optInt("httpPort", HostStore.DEFAULT_PORT)
        if (httpPort !in 1..65535) return false

        val host = HostInfo(
            name = payload.optString("name", address).ifBlank { address },
            address = address,
            port = httpPort,
            version = payload.optString("version", "?"),
            profileCount = payload.optJSONArray("profiles")?.length() ?: 0,
        )

        synchronized(hostsLock) { hosts[host.key] = host }
        return true
    }

    private fun prune() {
        val cutoff = System.currentTimeMillis() - STALE_AFTER_MS
        synchronized(hostsLock) {
            hosts.entries.removeAll { entry -> entry.value.lastSeenAt < cutoff }
        }
    }

    /** Не чаще раза в [EMIT_INTERVAL_MS]: иначе UI перерисовывается на каждый бикон. */
    private fun emitThrottled(force: Boolean = false) {
        val now = System.currentTimeMillis()
        if (!force && now - lastEmitAt < EMIT_INTERVAL_MS) return
        lastEmitAt = now
        emit()
    }

    private fun emit() = onHosts(snapshot())

    companion object {
        private const val TAG = "RudDiscovery"
        private const val BEACON_TYPE = "rud-panel-gateway"
        private const val DEFAULT_PORT = 8761
        private const val MAX_PACKET_BYTES = 8192
        private const val RECEIVE_TIMEOUT_MS = 1500
        private const val STALE_AFTER_MS = 15_000L
        private const val EMIT_INTERVAL_MS = 700L
    }
}

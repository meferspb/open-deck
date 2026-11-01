package com.rudpanel.gateway

import android.content.Context

/**
 * Последний успешно использованный хост — чтобы при следующем запуске
 * не искать его заново.
 */
class HostStore(context: Context) {

    private val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    fun lastHost(): HostInfo? {
        val address = prefs.getString(KEY_ADDRESS, null) ?: return null
        val port = prefs.getInt(KEY_PORT, DEFAULT_PORT)
        val name = prefs.getString(KEY_NAME, address) ?: address
        return HostInfo(
            name = name,
            address = address,
            port = port,
            version = "?",
            profileCount = 0,
        )
    }
    fun save(host: HostInfo) {
        prefs.edit()
            .putString(KEY_ADDRESS, host.address)
            .putInt(KEY_PORT, host.port)
            .putString(KEY_NAME, host.name)
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val PREFS_NAME = "rud_gateway"
        private const val KEY_ADDRESS = "last_address"
        private const val KEY_PORT = "last_port"
        private const val KEY_NAME = "last_name"
        val DEFAULT_PORT: Int = BuildConfig.DEFAULT_PORT
    }
}

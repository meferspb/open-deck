package com.rudpanel.gateway

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/** Реквизиты поддержки автора, полученные с хоста. */
data class DonationLink(
    val label: String,
    val url: String?,
    val value: String?,
)

data class DonationInfo(
    val author: String,
    val message: String,
    val links: List<DonationLink>,
)

/**
 * HTTP-проверки хоста. Никаких сторонних библиотек: HttpURLConnection
 * достаточно для трёх небольших GET-запросов.
 */
object HostApi {

    private const val CONNECT_TIMEOUT_MS = 2500
    private const val READ_TIMEOUT_MS = 3500

    /** Хост отвечает как шлюз (`/api/health` → status=ok). */
    fun isGateway(host: HostInfo): Boolean = try {
        val json = getJson("${host.origin}/api/health")
        json?.optString("status") == "ok"
    } catch (error: Exception) {
        false
    }

    /** Проверка целостности интерфейса на хосте (условие лицензии). */
    fun integrityVerified(host: HostInfo): Boolean = try {
        val json = getJson("${host.origin}/api/integrity")
        json?.optBoolean("verified", false) ?: false
    } catch (error: Exception) {
        false
    }

    /** Реквизиты поддержки автора (единственный источник — конфиг хоста). */
    fun donation(host: HostInfo): DonationInfo? = try {
        val json = getJson("${host.origin}/api/donation")
        if (json == null) {
            null
        } else {
            DonationInfo(
                author = json.optString("author", ""),
                message = json.optString("message", ""),
                links = parseLinks(json.optJSONArray("links")),
            )
        }
    } catch (error: Exception) {
        null
    }

    private fun parseLinks(array: JSONArray?): List<DonationLink> {
        if (array == null) return emptyList()
        val links = mutableListOf<DonationLink>()
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            links.add(
                DonationLink(
                    label = item.optString("label", "Поддержка"),
                    url = item.optString("url").takeIf { it.isNotBlank() },
                    value = item.optString("value").takeIf { it.isNotBlank() },
                ),
            )
        }
        return links
    }

    private fun getJson(url: String): JSONObject? {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            useCaches = false
            setRequestProperty("Accept", "application/json")
        }
        return try {
            if (connection.responseCode != HttpURLConnection.HTTP_OK) {
                null
            } else {
                val body = connection.inputStream.bufferedReader().use { it.readText() }
                if (body.isBlank()) null else JSONObject(body)
            }
        } finally {
            connection.disconnect()
        }
    }
}

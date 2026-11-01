package com.rudpanel.gateway

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast

/**
 * Единственная Activity приложения.
 *
 * Два экрана: подключение (поиск хоста, ручной IP, блок поддержки автора) и
 * панель (WebView с веб-клиентом хоста). Панель показывает те же профили,
 * приборы и жест-контролы, что и браузер, — отдельный движок не нужен.
 */
class MainActivity : Activity() {

    private lateinit var root: FrameLayout
    private lateinit var store: HostStore
    private lateinit var discovery: DiscoveryClient

    private var setupView: View? = null
    private var webView: WebView? = null
    private var connectedHost: HostInfo? = null

    /** Текущий диалог: закрываем при смене экрана и в onDestroy, иначе утечка окна. */
    private var currentDialog: AlertDialog? = null

    /** Номер попытки подключения: поздний ответ прошлой попытки игнорируется. */
    private var probeToken = 0
    private var probing = false

    /** Пока идёт загрузка реквизитов, повторные нажатия не плодят диалоги. */
    private var donationLoading = false

    /** Явное сообщение (ошибка/проверка) не должно затираться поиском хостов. */
    private var statusPinned = false

    /** Подпись последнего списка хостов — чтобы не перерисовывать его зря. */
    private var hostsSignature = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        root = FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        setContentView(root)

        store = HostStore(this)
        discovery = DiscoveryClient(
            onHosts = { hosts -> runOnUiThread { onHostsChanged(hosts) } },
            onError = { message ->
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        setStatus(getString(R.string.discovery_failed, message), pin = true)
                    }
                }
            },
        )
        discovery.start()

        enterImmersive()
        showSetup(null)

        // Прошлый хост пробуем один раз и молча: если его нет — остаёмся на setup.
        store.lastHost()?.let { host -> probeAndConnect(host, auto = true) }
    }

    // ------------------------------------------------------------------
    // Жизненный цикл
    // ------------------------------------------------------------------
    override fun onResume() {
        super.onResume()
        enterImmersive()
        webView?.onResume()
    }

    override fun onPause() {
        webView?.onPause()
        // Сессия входа живёт в cookie WebView: сохраняем её на диск, чтобы
        // после перезапуска приложения не вводить пароль заново.
        CookieManager.getInstance().flush()
        super.onPause()
    }

    override fun onDestroy() {
        currentDialog?.dismiss()
        currentDialog = null
        discovery.stop()
        webView?.let { view ->
            root.removeView(view)
            view.destroy()
        }
        webView = null
        super.onDestroy()
    }

    @Suppress("DEPRECATION", "OVERRIDE_DEPRECATION")
    override fun onBackPressed() {
        if (webView != null) {
            showSetup(null)
        } else {
            super.onBackPressed()
        }
    }

    @Suppress("DEPRECATION")
    private fun enterImmersive() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let { controller ->
                controller.hide(WindowInsets.Type.systemBars())
                controller.systemBarsBehavior =
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility =
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or
                    View.SYSTEM_UI_FLAG_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                    View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                    View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        }
    }

    // ------------------------------------------------------------------
    // Экран подключения
    // ------------------------------------------------------------------
    @SuppressLint("InflateParams")
    private fun showSetup(message: String?) {
        dismissDialog()
        // Экран настройки не должен удерживать экран включённым.
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        webView?.let { view ->
            root.removeView(view)
            view.destroy()
        }
        webView = null
        connectedHost = null

        val view = layoutInflater.inflate(R.layout.view_setup, root, false)
        root.removeAllViews()
        root.addView(view)
        setupView = view

        statusPinned = false
        hostsSignature = ""

        val status = view.findViewById<TextView>(R.id.status)
        val manual = view.findViewById<EditText>(R.id.manualHost)
        val connect = view.findViewById<Button>(R.id.connectButton)
        val donation = view.findViewById<TextView>(R.id.donationBar)

        status.text = message ?: getString(R.string.setup_status_searching)
        if (message != null) statusPinned = true

        manual.setText(
            store.lastHost()?.let { host -> "${host.address}:${host.port}" } ?: defaultHostHint(),
        )

        connect.setOnClickListener {
            val host = parseHostInput(manual.text.toString())
            if (host == null) {
                setStatus(getString(R.string.setup_bad_address), pin = true)
            } else {
                probeAndConnect(host, auto = false)
            }
        }
        donation.setOnClickListener { showDonationDialog() }

        renderHosts(discovery.snapshot())
        // Если приёмник упал (например, порт был занят), пробуем поднять снова.
        discovery.start()
    }

    private fun onHostsChanged(hosts: List<HostInfo>) {
        if (setupView == null || isFinishing || isDestroyed) return
        renderHosts(hosts)

        if (probing || statusPinned) return
        setStatus(
            if (hosts.isEmpty()) {
                getString(R.string.setup_status_none)
            } else {
                getString(R.string.setup_status_found, hosts.size)
            },
        )
    }

    private fun renderHosts(hosts: List<HostInfo>) {
        val container = setupView?.findViewById<LinearLayout>(R.id.hostList) ?: return

        val signature = hosts.joinToString("|") {
            "${it.key}:${it.name}:${it.profileCount}:${it.authRequired}"
        }
        if (signature == hostsSignature) return
        hostsSignature = signature

        container.removeAllViews()

        if (hosts.isEmpty()) {
            container.addView(
                TextView(this).apply {
                    text = getString(R.string.setup_status_searching)
                    setTextColor(getColor(R.color.muted))
                    textSize = 13f
                    setPadding(dp(4), dp(4), dp(4), dp(12))
                },
            )
            return
        }

        for (host in hosts) {
            val card = TextView(this).apply {
                text = getString(
                    R.string.setup_host_card,
                    if (host.authRequired) "🔒 ${host.name}" else host.name,
                    "${host.address}:${host.port}",
                    host.version,
                    host.profileCount,
                )
                setTextColor(getColor(R.color.text))
                textSize = 14f
                setLineSpacing(dp(3).toFloat(), 1f)
                setPadding(dp(14), dp(12), dp(14), dp(12))
                setBackgroundResource(R.drawable.bg_card)
                isClickable = true
                isFocusable = true
                layoutParams = LinearLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT,
                    ViewGroup.LayoutParams.WRAP_CONTENT,
                ).apply { bottomMargin = dp(8) }
                setOnClickListener { probeAndConnect(host, auto = false) }
            }
            container.addView(card)
        }
    }

    // ------------------------------------------------------------------
    // Подключение
    // ------------------------------------------------------------------
    private fun probeAndConnect(host: HostInfo, auto: Boolean) {
        probeToken += 1
        val token = probeToken
        probing = true
        setStatus(getString(R.string.setup_status_probing, "${host.address}:${host.port}"), pin = true)

        Thread {
            val alive = HostApi.isGateway(host)
            val integrity = alive && HostApi.integrityVerified(host)

            runOnUiThread {
                if (token != probeToken) return@runOnUiThread
                probing = false
                if (isFinishing || isDestroyed) return@runOnUiThread

                when {
                    // Автоподключение при старте не должно выбрасывать на setup:
                    // пользователь мог уже начать что-то вводить.
                    !alive -> if (auto) {
                        setStatus(getString(R.string.host_unreachable), pin = false)
                    } else {
                        showError(getString(R.string.host_unreachable))
                    }

                    !integrity -> showIntegrityLock(host)
                    else -> openPanel(host)
                }
            }
        }.start()
    }

    private fun setStatus(text: String, pin: Boolean = false) {
        statusPinned = pin
        val status = setupView?.findViewById<TextView>(R.id.status) ?: return
        status.setTextColor(getColor(R.color.accent))
        status.text = text
    }

    private fun dismissDialog() {
        currentDialog?.dismiss()
        currentDialog = null
    }

    private fun showDialog(configure: AlertDialog.Builder.() -> Unit) {
        if (isFinishing || isDestroyed) return
        dismissDialog()
        val dialog = AlertDialog.Builder(this).apply(configure).create()
        dialog.setOnDismissListener { if (currentDialog === dialog) currentDialog = null }
        currentDialog = dialog
        dialog.show()
    }

    private fun showError(message: String) {
        showDialog {
            setTitle(R.string.app_name)
            setMessage(message)
            setCancelable(false)
            setPositiveButton(android.R.string.ok) { _, _ -> showSetup(null) }
        }
    }

    private fun showIntegrityLock(host: HostInfo) {
        showDialog {
            setTitle(R.string.integrity_title)
            setMessage(R.string.integrity_message)
            setCancelable(false)
            setPositiveButton(R.string.action_retry) { _, _ -> probeAndConnect(host, auto = false) }
            setNegativeButton(R.string.action_other_host) { _, _ -> showSetup(null) }
        }
    }

    /** Адрес из настроек сборки — подсказка, если хост ещё не сохранён. */
    private fun defaultHostHint(): String {
        val host = BuildConfig.DEFAULT_HOST
        return if (host.isBlank()) "" else "$host:${BuildConfig.DEFAULT_PORT}"
    }

    /** Адрес: `192.168.1.10`, `192.168.1.10:8760` или полный URL. Только IPv4/имя. */
    private fun parseHostInput(raw: String): HostInfo? {
        var text = raw.trim()
        if (text.isEmpty()) return null
        if (text.any { it.isWhitespace() }) return null
        // IPv6 и «лишние» двоеточия не поддерживаются осознанно.
        if (text.startsWith("[") || text.count { it == ':' } > 1) return null

        text = text.removePrefix("http://").removePrefix("https://").trimEnd('/')
        val parts = text.split(':')
        val address = parts[0].trim()
        if (address.isEmpty() || address.contains('/')) return null
        if (!HOST_PATTERN.matches(address)) return null

        val port = if (parts.size > 1) parts[1].toIntOrNull() ?: return null
        else HostStore.DEFAULT_PORT
        if (port !in 1..65535) return null

        return HostInfo(
            name = address,
            address = address,
            port = port,
            version = "?",
            profileCount = 0,
        )
    }

    // ------------------------------------------------------------------
    // Панель
    // ------------------------------------------------------------------
    @SuppressLint("SetJavaScriptEnabled")
    private fun openPanel(host: HostInfo) {
        if (isFinishing || isDestroyed) return

        dismissDialog()
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        store.save(host)
        connectedHost = host
        setupView = null

        val url = "${host.origin}/?device=${deviceClass()}&frame=0"
        val web = WebView(this)
        web.setBackgroundColor(Color.BLACK)

        with(web.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_NO_CACHE
            mediaPlaybackRequiresUserGesture = false
            useWideViewPort = true
            loadWithOverviewMode = false
            setSupportZoom(false)
            builtInZoomControls = false
            displayZoomControls = false
            allowFileAccess = false
            allowContentAccess = false
            CookieManager.getInstance().setAcceptCookie(true)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
        }

        web.webChromeClient = WebChromeClient()
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?,
                request: WebResourceRequest?,
            ): Boolean {
                val uri = request?.url ?: return true
                if (uri.scheme == "about") return false

                val sameAddress = uri.host?.equals(host.address, ignoreCase = true) == true
                val sameName = uri.host?.equals(host.name, ignoreCase = true) == true
                val samePort = uri.port == -1 || uri.port == host.port
                if ((sameAddress || sameName) && samePort) return false

                // Молча терять переход нельзя: пользователь решит, что панель зависла.
                Toast.makeText(this@MainActivity, R.string.link_blocked, Toast.LENGTH_SHORT).show()
                return true
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?,
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true && webView === view) {
                    root.post {
                        if (webView !== view || isFinishing || isDestroyed) return@post
                        showDialog {
                            setTitle(R.string.app_name)
                            setMessage(getString(R.string.panel_load_error, host.address))
                            setCancelable(false)
                            setPositiveButton(R.string.action_retry) { _, _ ->
                                probeAndConnect(host, auto = false)
                            }
                            setNegativeButton(R.string.action_other_host) { _, _ ->
                                showSetup(null)
                            }
                        }
                    }
                }
            }
        }

        root.removeAllViews()
        root.addView(
            web,
            FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            ),
        )
        webView = web
        web.loadUrl(url)
        web.requestFocus()
    }

    /** Форм-фактор по размеру экрана: телефон / малый / большой планшет. */
    private fun deviceClass(): String {
        val smallestWidth = resources.configuration.smallestScreenWidthDp
        return when {
            smallestWidth >= 900 -> "tablet-lg"
            smallestWidth >= 600 -> "tablet-sm"
            else -> "phone"
        }
    }

    // ------------------------------------------------------------------
    // Блок поддержки автора (условие лицензии)
    // ------------------------------------------------------------------
    private fun showDonationDialog() {
        if (donationLoading) return

        val host = connectedHost ?: discovery.snapshot().firstOrNull() ?: store.lastHost()
        if (host == null) {
            showDialog {
                setTitle(R.string.donation_title)
                setMessage(R.string.donation_offline)
                setPositiveButton(android.R.string.ok, null)
            }
            return
        }

        donationLoading = true
        Thread {
            val donation = HostApi.donation(host)
            runOnUiThread {
                donationLoading = false
                if (isFinishing || isDestroyed) return@runOnUiThread
                renderDonation(host, donation)
            }
        }.start()
    }

    private fun renderDonation(host: HostInfo, donation: DonationInfo?) {
        if (donation == null) {
            showDialog {
                setTitle(R.string.donation_title)
                setMessage(getString(R.string.donation_unavailable, host.address))
                setPositiveButton(android.R.string.ok, null)
            }
            return
        }

        val title = if (donation.author.isNotBlank()) {
            "${getString(R.string.donation_title)} · ${donation.author}"
        } else {
            getString(R.string.donation_title)
        }
        val message = buildString {
            append(donation.message.ifBlank { getString(R.string.donation_default_message) })
            if (donation.author.isNotBlank()) {
                append("\n\n")
                append(getString(R.string.donation_author, donation.author))
            }
        }

        if (donation.links.isEmpty()) {
            showDialog {
                setTitle(title)
                setMessage(message)
                setPositiveButton(android.R.string.ok, null)
            }
            return
        }

        val entries = donation.links.map { link ->
            val target = link.url ?: link.value ?: ""
            if (target.isBlank()) link.label else "${link.label}\n$target"
        }.toTypedArray()

        showDialog {
            setTitle(title)
            setItems(entries) { _, which -> openDonationLink(donation.links[which]) }
            setPositiveButton(R.string.action_close, null)
        }
    }

    private fun openDonationLink(link: DonationLink) {
        val url = link.url ?: return
        val uri = Uri.parse(url)
        // Только веб-ссылки: file://, content://, intent: от хоста не принимаем.
        if (uri.scheme != "http" && uri.scheme != "https") {
            Toast.makeText(this, R.string.donation_no_browser, Toast.LENGTH_SHORT).show()
            return
        }
        try {
            startActivity(Intent(Intent.ACTION_VIEW, uri))
        } catch (error: Exception) {
            Toast.makeText(this, R.string.donation_no_browser, Toast.LENGTH_SHORT).show()
        }
    }

    private fun dp(value: Int): Int =
        (value * resources.displayMetrics.density).toInt()

    companion object {
        /** Имя хоста или IPv4-адрес: без пробелов, слэшей и скобок. */
        private val HOST_PATTERN = Regex("^[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?$")
    }
}

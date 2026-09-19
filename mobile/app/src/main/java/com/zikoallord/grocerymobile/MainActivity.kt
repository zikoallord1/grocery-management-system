package com.zikoallord.grocerymobile

import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import android.widget.Button
import android.widget.ImageButton
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : AppCompatActivity() {
    private val cameras = mutableListOf<CameraConfig>()
    private val players = mutableListOf<ExoPlayer>()
    private lateinit var content: LinearLayout
    private lateinit var syncStatus: TextView
    private lateinit var summary: TextView
    private lateinit var navHome: TextView
    private lateinit var navSales: TextView
    private lateinit var navStock: TextView
    private lateinit var navReports: TextView
    private lateinit var navCameras: TextView
    private val navItems = mutableListOf<TextView>()
    private val prefs by lazy { getSharedPreferences("mobile", MODE_PRIVATE) }
    private val cameraPrefs by lazy { getSharedPreferences("cameras", MODE_PRIVATE) }

    private val blue = Color.rgb(0, 92, 190)
    private val darkBlue = Color.rgb(0, 54, 112)
    private val lightBlue = Color.rgb(239, 247, 255)
    private val textBlue = Color.rgb(0, 58, 120)
    private val green = Color.rgb(16, 174, 105)
    private val orange = Color.rgb(245, 139, 18)
    private val purple = Color.rgb(104, 67, 211)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        loadCameras()
        buildUi()
        showHome()
        refreshFromDesktop()
    }

    private fun rounded(fill: Int, stroke: Int = Color.TRANSPARENT, radius: Float = 18f): GradientDrawable =
        GradientDrawable().apply {
            setColor(fill)
            if (stroke != Color.TRANSPARENT) setStroke(1, stroke)
            cornerRadius = radius
        }

    private fun text(value: String, size: Float, color: Int = textBlue, bold: Boolean = false): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
        gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(247, 250, 254))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }

        val header = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(18, 16, 18, 14)
            background = rounded(darkBlue, radius = 0f)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val headerRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val titleBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_VERTICAL }
        titleBox.addView(text("نظام الماركت المحاسبي", 18f, Color.WHITE, true))
        titleBox.addView(text("إدارة شاملة .. لمتجرك بكل سهولة", 12f, Color.rgb(220, 235, 255)))
        headerRow.addView(titleBox, LinearLayout.LayoutParams(0, -2, 1f))
        val bell = text("🔔", 22f, Color.WHITE, false).apply { gravity = Gravity.CENTER }
        bell.setPadding(10, 4, 10, 4)
        headerRow.addView(bell, LinearLayout.LayoutParams(52, 52))
        header.addView(headerRow)
        root.addView(header)

        val ticker = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(10, 7, 10, 7)
            background = rounded(Color.WHITE, Color.rgb(205, 224, 244), 14f)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        ticker.addView(text("التنبيهات", 12f, blue, true), LinearLayout.LayoutParams(75, 38))
        syncStatus = text("● لم تتم المزامنة بعد", 12f, Color.DKGRAY)
        syncStatus.gravity = Gravity.CENTER
        ticker.addView(syncStatus, LinearLayout.LayoutParams(0, 38, 1f))
        val settings = text("⚙", 22f, blue, true).apply { gravity = Gravity.CENTER; setOnClickListener { showServerDialog() } }
        ticker.addView(settings, LinearLayout.LayoutParams(48, 38))
        val tickerLp = LinearLayout.LayoutParams(-1, 54); tickerLp.setMargins(10, 8, 10, 4)
        root.addView(ticker, tickerLp)

        val scroll = ScrollView(this)
        content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(12, 8, 12, 18)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))

        val workspace = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.TOP
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val navScroll = ScrollView(this).apply {
            isFillViewport = true
            background = rounded(Color.WHITE, Color.rgb(205, 224, 244), 0f)
        }
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.TOP
            setPadding(5, 6, 5, 8)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        navHome = addNavButton(nav, "الرئيسية") { showHome() }
        navSales = addNavButton(nav, "المبيعات") { showSales() }
        addNavButton(nav, "المشتريات") { showModule("المشتريات", "إدارة فواتير الشراء والموردين والمدفوعات.") }
        addNavButton(nav, "الأصناف") { showModule("الأصناف", "إدارة الأصناف والوحدات والباركود والأسعار.") }
        navStock = addNavButton(nav, "المخزون") { showModule("المخزون", "متابعة الكميات والحركات والتنبيهات.") }
        addNavButton(nav, "العملاء") { showModule("العملاء", "إدارة العملاء وكشوف الحساب والتحصيلات.") }
        addNavButton(nav, "الموردون") { showModule("الموردون", "إدارة الموردين وكشوف الحساب والمدفوعات.") }
        addNavButton(nav, "المصروفات") { showModule("المصروفات", "تسجيل ومراجعة المصروفات ووسائل الدفع.") }
        addNavButton(nav, "الصناديق\nوالحسابات") { showModule("الصناديق والحسابات", "متابعة الحسابات والتحويلات المالية.") }
        addNavButton(nav, "المرتجعات") { showModule("المرتجعات", "إرجاع العمليات وفق الصلاحيات دون حذف الأصل.") }
        navReports = addNavButton(nav, "التقارير") { showModule("التقارير", "تقارير فعلية بفترة وتصفية قابلة للتخصيص.") }
        addNavButton(nav, "الإعدادات") { showModule("الإعدادات", "إعدادات السوق والمستخدمين والترخيص.") }
        navCameras = addNavButton(nav, "الكاميرات") { showCameras() }
        navScroll.addView(nav)
        workspace.addView(navScroll, LinearLayout.LayoutParams(112, -1))
        workspace.addView(scroll, LinearLayout.LayoutParams(0, 0, 1f))
        root.removeView(scroll)
        root.addView(workspace, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    private fun addNavButton(parent: LinearLayout, label: String, action: () -> Unit): TextView {
        val button = text(label, 11f, Color.rgb(28, 70, 120), true).apply {
            gravity = Gravity.CENTER
            setPadding(2, 5, 2, 5)
            setOnClickListener { action() }
            background = rounded(Color.WHITE, Color.TRANSPARENT, 12f)
        }
        parent.addView(button, LinearLayout.LayoutParams(-1, 52))
        navItems.add(button)
        return button
    }

    private fun markNav(active: TextView) {
        navItems.forEach {
            it.background = rounded(if (it == active) blue else Color.WHITE, Color.TRANSPARENT, 12f)
            it.setTextColor(if (it == active) Color.WHITE else Color.rgb(28, 70, 120))
        }
    }

    private fun addSectionTitle(title: String, action: String? = null) {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        val h = text(title, 17f, textBlue, true)
        row.addView(h, LinearLayout.LayoutParams(0, 48, 1f))
        if (action != null) row.addView(text(action, 11f, blue, true).apply { gravity = Gravity.CENTER })
        content.addView(row)
    }

    private fun addCard(title: String, value: String, icon: String, color: Int) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(14, 12, 14, 12)
            background = rounded(Color.WHITE, Color.rgb(215, 230, 246), 16f)
            elevation = 1f
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val iconView = text(icon, 21f, Color.WHITE, true).apply { gravity = Gravity.CENTER; background = rounded(color, Color.TRANSPARENT, 14f) }
        card.addView(iconView, LinearLayout.LayoutParams(48, 48))
        val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER_VERTICAL; setPadding(12, 0, 8, 0) }
        info.addView(text(title, 12f, Color.DKGRAY, false))
        info.addView(text(value, 18f, textBlue, true))
        card.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
        val lp = LinearLayout.LayoutParams(-1, 76); lp.setMargins(0, 6, 0, 0)
        content.addView(card, lp)
    }

    private fun showHome() {
        releasePlayers()
        content.removeAllViews()
        markNav(navHome)
        val hero = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(18, 18, 18, 18)
            background = rounded(darkBlue, Color.TRANSPARENT, 20f)
        }
        hero.addView(text("نظام الماركت المحاسبي", 20f, Color.WHITE, true).apply { gravity = Gravity.CENTER })
        hero.addView(text("إدارة متكاملة .. مبيعات ومخزون ومحاسبة وكاميرات مراقبة", 12f, Color.rgb(220, 235, 255)).apply { gravity = Gravity.CENTER })
        content.addView(hero, LinearLayout.LayoutParams(-1, 112))

        addSectionTitle("سوق الوحدة - الفرع الرئيسي")
        summary = text("بيانات النظام ستظهر هنا عند الاتصال بجهاز البقالة.", 13f, textBlue)
        summary.setPadding(16, 12, 16, 12)
        summary.background = rounded(Color.WHITE, Color.rgb(215, 230, 246), 16f)
        content.addView(summary, LinearLayout.LayoutParams(-1, 72))

        addSectionTitle("ملخص اليوم")
        addCard("المبيعات اليوم", "—", "↗", green)
        addCard("المشتريات اليوم", "—", "🛒", blue)
        addCard("المخزون", "—", "▣", orange)
        addCard("الأرباح اليوم", "—", "↗", purple)

        addSectionTitle("العمليات السريعة")
        val actions = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        listOf("فاتورة بيع جديدة", "فاتورة شراء جديدة", "إضافة صنف", "تقارير", "الحسابات", "كاميرات المراقبة").forEach { label ->
            val b = text("$label  ›", 13f, blue, true).apply {
                setPadding(16, 0, 16, 0)
                gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
                background = rounded(Color.WHITE, Color.rgb(215, 230, 246), 14f)
                setOnClickListener { if (label == "كاميرات المراقبة") showCameras() else if (label == "تقارير") showModule("التقارير", "التقارير والملخصات التشغيلية والمالية.") else showModule(label, "متابعة العملية وإدارتها من النظام.") }
            }

            private fun showSales() {
                releasePlayers()
                content.removeAllViews()
                markNav(navSales)
                addSectionTitle("المبيعات", "فاتورة جديدة")
                val search = EditText(this).apply {
                    hint = "ابحث باسم الصنف أو امسح الباركود"
                    textSize = 14f
                    setSingleLine(true)
                    setPadding(16, 0, 16, 0)
                    layoutDirection = View.LAYOUT_DIRECTION_RTL
                    background = rounded(Color.WHITE, Color.rgb(170, 201, 232), 14f)
                }
                content.addView(search, LinearLayout.LayoutParams(-1, 52).apply { setMargins(0, 4, 0, 8) })
                val cart = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(12, 8, 12, 8)
                    background = rounded(Color.WHITE, Color.rgb(210, 228, 247), 16f)
                }
                cart.addView(text("تفاصيل الفاتورة", 15f, textBlue, true))
                cart.addView(text("لم تتم إضافة أصناف بعد. استخدم البحث أو قارئ الباركود لإضافة الصنف.", 13f, Color.DKGRAY).apply {
                    setPadding(0, 12, 0, 12)
                })
                val line = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    layoutDirection = View.LAYOUT_DIRECTION_RTL
                }
                line.addView(text("الكمية", 12f, Color.DKGRAY, true), LinearLayout.LayoutParams(0, 42, 1f))
                line.addView(EditText(this).apply { hint = "1"; inputType = 2; gravity = Gravity.CENTER; setSingleLine(true) }, LinearLayout.LayoutParams(58, 42))
                line.addView(text("السعر", 12f, Color.DKGRAY, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(0, 42, 1f))
                line.addView(EditText(this).apply { hint = "0.00"; inputType = 2 or 8192; gravity = Gravity.CENTER; setSingleLine(true) }, LinearLayout.LayoutParams(82, 42))
                cart.addView(line)
                content.addView(cart, LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, 0, 0, 8) })
                val totals = LinearLayout(this).apply {
                    orientation = LinearLayout.VERTICAL
                    setPadding(14, 10, 14, 10)
                    background = rounded(darkBlue, Color.TRANSPARENT, 16f)
                }
                listOf("الإجمالي", "المدفوع", "المتبقي").forEach { label ->
                    val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
                    row.addView(text(label, 14f, Color.WHITE, true), LinearLayout.LayoutParams(0, 38, 1f))
                    row.addView(text("0.00", 14f, Color.WHITE, true).apply { gravity = Gravity.LEFT or Gravity.CENTER_VERTICAL }, LinearLayout.LayoutParams(100, 38))
                    totals.addView(row)
                }
                totals.addView(text("طرق الدفع (يمكن الجمع بينها)", 13f, Color.rgb(220, 235, 255), true).apply { setPadding(0, 8, 0, 4) })
                val methods = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
                listOf("نقدًا", "محفظة إلكترونية", "آجل", "تحويل").forEach { method ->
                    val b = text(method, 11f, textBlue, true).apply {
                        gravity = Gravity.CENTER
                        background = rounded(Color.WHITE, Color.TRANSPARENT, 12f)
                        setOnClickListener { setBackgroundColor(Color.rgb(210, 235, 255)) }
                    }
                    methods.addView(b, LinearLayout.LayoutParams(0, 44, 1f).apply { setMargins(2, 2, 2, 2) })
                }
                totals.addView(methods)
                content.addView(totals, LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, 0, 0, 8) })
                val camerasToggle = text("كاميرات المراقبة  ▾", 14f, blue, true).apply {
                    gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
                    background = rounded(Color.WHITE, Color.rgb(205, 224, 244), 14f)
                    setPadding(14, 0, 14, 0)
                }
                val cameraHint = text("قسم اختياري قابل للطي — لا يعرض تلقائيًا أثناء البيع.", 12f, Color.DKGRAY).apply {
                    setPadding(14, 10, 14, 10)
                    visibility = View.GONE
                }
                camerasToggle.setOnClickListener { cameraHint.visibility = if (cameraHint.visibility == View.GONE) View.VISIBLE else View.GONE }
                content.addView(camerasToggle, LinearLayout.LayoutParams(-1, 48))
                content.addView(cameraHint, LinearLayout.LayoutParams(-1, -2))
            }
            val lp = LinearLayout.LayoutParams(-1, 54); lp.setMargins(0, 5, 0, 0); actions.addView(b, lp)
        }
        content.addView(actions)
    }

    private fun showModule(title: String, message: String) {
        releasePlayers()
        content.removeAllViews()
        when (title) {
            "المبيعات" -> markNav(navSales)
            "المخزون" -> markNav(navStock)
            "التقارير" -> markNav(navReports)
            else -> { }
        }
        addSectionTitle(title, "‹ رجوع")
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(18, 18, 18, 18)
            background = rounded(Color.WHITE, Color.rgb(210, 228, 247), 18f)
        }
        card.addView(text(message, 16f, textBlue, true))
        card.addView(text("هذه الشاشة مخصصة للعملية نفسها، وتبقى البيانات من مصدر النظام دون إنشاء بيانات افتراضية.", 12f, Color.DKGRAY).apply { setPadding(0, 10, 0, 4) })
        content.addView(card, LinearLayout.LayoutParams(-1, -2))
        val actions = listOf("جديد", "بحث", "تحديث")
        actions.forEach { label ->
            val b = text(label, 13f, blue, true).apply { gravity = Gravity.CENTER; background = rounded(lightBlue, Color.rgb(195, 220, 247), 14f) }
            val lp = LinearLayout.LayoutParams(-1, 52); lp.setMargins(0, 8, 0, 0); content.addView(b, lp)
        }
    }

    private fun showCameras() {
        releasePlayers()
        content.removeAllViews()
        markNav(navCameras)
        addSectionTitle("كاميرات المراقبة", "● مباشر")
        val info = text("الكاميرات خيار مستقل داخل النظام، ولا تفتح تلقائيًا عند تشغيل التطبيق.", 12f, Color.DKGRAY)
        info.setPadding(14, 12, 14, 12); info.background = rounded(Color.WHITE, Color.rgb(215, 230, 246), 14f)
        content.addView(info, LinearLayout.LayoutParams(-1, -2))
        if (cameras.isEmpty()) {
            val empty = text("لا توجد كاميرات مضافة بعد\nأضف كاميرا IP أو DVR/NVR باستخدام رابط RTSP.", 14f, Color.GRAY)
            empty.gravity = Gravity.CENTER; empty.setPadding(20, 42, 20, 42); empty.background = rounded(Color.WHITE, Color.rgb(215, 230, 246), 18f)
            val lp = LinearLayout.LayoutParams(-1, 170); lp.setMargins(0, 10, 0, 0); content.addView(empty, lp)
        } else cameras.forEach { addCameraCard(it) }
        val add = text("＋  إضافة كاميرا مراقبة", 15f, Color.WHITE, true).apply {
            gravity = Gravity.CENTER; background = rounded(blue, Color.TRANSPARENT, 16f); setOnClickListener { showAddCameraDialog() }
        }
        val lp = LinearLayout.LayoutParams(-1, 56); lp.setMargins(0, 10, 0, 0); content.addView(add, lp)
    }

    private fun serverUrl(): String = prefs.getString("server_url", "")?.trim()?.trimEnd('/') ?: ""

    private fun showServerDialog() {
        val input = EditText(this).apply { hint = "عنوان جهاز Windows"; setSingleLine(true); setText(serverUrl()) }
        AlertDialog.Builder(this).setTitle("الاتصال بالنظام").setMessage("أدخل عنوان جهاز Windows الذي يشغل النظام، ثم اختبر الاتصال.").setView(input).setNegativeButton("إلغاء", null).setPositiveButton("حفظ واختبار") { _, _ ->
            val value = input.text.toString().trim().trimEnd('/')
            if (value.isEmpty()) { prefs.edit().remove("server_url").apply(); syncStatus.text = "● لم يتم تحديد جهاز النظام" }
            else { prefs.edit().putString("server_url", value).apply(); refreshFromDesktop() }
        }.show()
    }

    private fun refreshFromDesktop() {
        val base = serverUrl()
        if (base.isEmpty()) { syncStatus.text = "● أدخل عنوان جهاز البقالة من زر الاتصال"; return }
        syncStatus.text = "● جاري المزامنة مع جهاز البقالة..."
        Thread {
            try {
                val connection = URL("$base/api/mobile/summary").openConnection() as HttpURLConnection
                connection.requestMethod = "GET"; connection.connectTimeout = 5000; connection.readTimeout = 7000
                val response = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }; connection.disconnect()
                val data = JSONObject(response)
                runOnUiThread {
                    if (data.optBoolean("ok")) {
                        if (::summary.isInitialized) summary.text = "مبيعات اليوم: ${money(data.optDouble("sales"))}   |   مشتريات: ${money(data.optDouble("purchases"))}\nالمصروفات: ${money(data.optDouble("expenses"))}   |   صافي الربح: ${money(data.optDouble("profit"))}\nذمم العملاء: ${money(data.optDouble("receivables"))}   |   ذمم الموردين: ${money(data.optDouble("payables"))}\nالصندوق: ${money(data.optDouble("cash"))}   |   أصناف منخفضة: ${data.optInt("low_stock")}"
                        syncStatus.text = "● متصل بالمزامنة — ${data.optString("date")}"; syncStatus.setTextColor(green)
                    } else { syncStatus.text = "● تعذر قراءة بيانات النظام" }
                }
            } catch (e: Exception) {
                runOnUiThread { syncStatus.text = "● غير متصل — تحقق من عنوان الجهاز والشبكة"; syncStatus.setTextColor(Color.rgb(190, 45, 45)) }
            }
        }.start()
    }

    private fun money(value: Double): String = String.format("%,.2f", value)

    private fun addCameraCard(camera: CameraConfig) {
        val card = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(10, 10, 10, 10); background = rounded(Color.WHITE, Color.rgb(210, 228, 247), 18f); layoutDirection = View.LAYOUT_DIRECTION_RTL }
        val title = text("${camera.name}    •    ${camera.location}", 14f, textBlue, true); title.setPadding(4, 6, 4, 8); card.addView(title)
        val playerView = PlayerView(this).apply { useController = true; setBackgroundColor(Color.BLACK); layoutParams = LinearLayout.LayoutParams(-1, 210) }
        card.addView(playerView)
        val status = text("● جاري الاتصال بالكاميرا...", 12f, orange); status.setPadding(4, 8, 4, 6); card.addView(status)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.RIGHT }
        val reconnect = text("إعادة الاتصال", 12f, blue, true).apply { setPadding(18, 8, 18, 8); setOnClickListener { playCamera(camera, playerView, status) } }
        val remove = text("حذف", 12f, Color.rgb(190, 45, 45), true).apply { setPadding(18, 8, 18, 8); setOnClickListener { cameras.remove(camera); saveCameras(); showCameras() } }
        actions.addView(remove); actions.addView(reconnect); card.addView(actions)
        val lp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT); lp.setMargins(0, 8, 0, 8); content.addView(card, lp)
        playCamera(camera, playerView, status)
    }

    private fun playCamera(camera: CameraConfig, view: PlayerView, status: TextView) {
        view.player?.release(); val player = ExoPlayer.Builder(this).build(); players.add(player); view.player = player
        player.setMediaItem(MediaItem.fromUri(Uri.parse(camera.rtspUrl)))
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) { when (state) { Player.STATE_BUFFERING -> status.text = "● جاري تحميل بث ${camera.name}..."; Player.STATE_READY -> status.text = "● الكاميرا متصلة ومباشرة"; Player.STATE_ENDED -> status.text = "● انتهى البث" } }
            override fun onPlayerError(error: androidx.media3.common.PlaybackException) { status.text = "● تعذر الاتصال: تحقق من رابط RTSP والشبكة" }
        })
        player.prepare(); player.playWhenReady = true
    }

    private fun showAddCameraDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(36, 10, 36, 0) }
        val name = EditText(this).apply { hint = "اسم الكاميرا" }
        val location = EditText(this).apply { hint = "الموقع - مثال: باب المحل" }
        val url = EditText(this).apply { hint = "رابط RTSP"; setSingleLine(true) }
        box.addView(name); box.addView(location); box.addView(url)
        AlertDialog.Builder(this).setTitle("إضافة كاميرا مراقبة").setView(box).setNegativeButton("إلغاء", null).setPositiveButton("حفظ واتصال") { _, _ ->
            val n = name.text.toString().trim(); val l = location.text.toString().trim().ifEmpty { "المحل" }; val u = url.text.toString().trim()
            if (n.isEmpty() || u.isEmpty()) Toast.makeText(this, "أدخل اسم الكاميرا ورابط RTSP", Toast.LENGTH_LONG).show()
            else { cameras.add(CameraConfig(n, l, u)); saveCameras(); showCameras() }
        }.show()
    }

    private fun loadCameras() {
        cameras.clear(); val raw = cameraPrefs.getString("items", "[]") ?: "[]"; val array = JSONArray(raw)
        for (i in 0 until array.length()) { val o = array.getJSONObject(i); cameras.add(CameraConfig(o.getString("name"), o.getString("location"), o.getString("url"))) }
    }

    private fun saveCameras() {
        val array = JSONArray(); cameras.forEach { camera -> array.put(JSONObject().apply { put("name", camera.name); put("location", camera.location); put("url", camera.rtspUrl) }) }
        cameraPrefs.edit().putString("items", array.toString()).apply()
    }

    private fun releasePlayers() { players.forEach { it.release() }; players.clear() }
    override fun onDestroy() { releasePlayers(); super.onDestroy() }
}

data class CameraConfig(val name: String, val location: String, val rtspUrl: String)
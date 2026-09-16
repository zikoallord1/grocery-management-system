package com.zikoallord.grocerymobile

import android.graphics.Color
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
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import org.json.JSONArray
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private val cameras = mutableListOf<CameraConfig>()
    private val players = mutableListOf<ExoPlayer>()
    private lateinit var content: LinearLayout
    private val prefs by lazy { getSharedPreferences("cameras", MODE_PRIVATE) }

    private val blue = Color.rgb(8, 91, 171)
    private val blueDark = Color.rgb(5, 62, 116)
    private val bg = Color.rgb(246, 248, 252)
    private val textDark = Color.rgb(25, 52, 78)
    private val muted = Color.rgb(102, 116, 132)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = blueDark
        window.navigationBarColor = Color.rgb(8, 28, 45)
        loadCameras()
        showHome()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun baseRoot(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        fitsSystemWindows = true
    }

    private fun makeHeader(title: String, subtitle: String = ""): LinearLayout {
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(blue)
            setPadding(dp(20), dp(14), dp(20), dp(14))
            gravity = Gravity.CENTER_VERTICAL
        }
        TextView(this).apply {
            text = title
            textSize = 22f
            setTextColor(Color.WHITE)
            gravity = Gravity.RIGHT
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            header.addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        if (subtitle.isNotEmpty()) {
            TextView(this).apply {
                text = subtitle
                textSize = 13f
                setTextColor(Color.rgb(225, 239, 255))
                gravity = Gravity.RIGHT
                setPadding(0, dp(3), 0, 0)
                header.addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
            }
        }
        return header
    }

    private fun makeTicker(): TextView = TextView(this).apply {
        text = "● حالة المزامنة: جاهز    •    المبيعات اليوم: 12,450 ريال    •    تنبيهات المخزون: 3"
        textSize = 12f
        setTextColor(blue)
        setBackgroundColor(Color.WHITE)
        gravity = Gravity.CENTER
        setPadding(dp(10), dp(8), dp(10), dp(8))
    }

    private fun makeNav(active: String): LinearLayout {
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(blue)
            setPadding(dp(6), dp(6), dp(6), dp(6))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val items = listOf("الرئيسية", "المبيعات", "المخزون", "الكاميرات", "الإعدادات")
        items.forEach { label ->
            val button = TextView(this).apply {
                text = if (label == active) "●  $label" else label
                textSize = 11f
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                setPadding(dp(3), dp(9), dp(3), dp(9))
                if (label == active) setBackgroundColor(Color.rgb(24, 124, 220))
                setOnClickListener {
                    when (label) {
                        "الرئيسية" -> showHome()
                        "الكاميرات" -> showCameras()
                        else -> Toast.makeText(this@MainActivity, "سيتم فتح قسم $label ضمن النسخة المتكاملة", Toast.LENGTH_SHORT).show()
                    }
                }
            }
            nav.addView(button, LinearLayout.LayoutParams(0, dp(58), 1f))
        }
        return nav
    }

    private fun card(title: String, value: String, hint: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(Color.WHITE)
        setPadding(dp(16), dp(14), dp(16), dp(14))
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        TextView(this@MainActivity).apply {
            text = title
            textSize = 13f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        TextView(this@MainActivity).apply {
            text = value
            textSize = 22f
            setTextColor(textDark)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            setPadding(0, dp(5), 0, dp(2))
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        TextView(this@MainActivity).apply {
            text = hint
            textSize = 11f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
    }

    private fun showHome() {
        releasePlayers()
        val root = baseRoot()
        root.addView(makeHeader("نظام البقالة المحاسبي", "إدارة متجرك من الجوال"), LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(makeTicker(), LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))

        val scroll = ScrollView(this)
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(16), dp(14), dp(18))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        TextView(this).apply {
            text = "لوحة المتابعة"
            textSize = 22f
            setTextColor(textDark)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            body.addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        TextView(this).apply {
            text = "مرحبًا بك — اختر القسم الذي تريد إدارته"
            textSize = 14f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            setPadding(0, dp(5), 0, dp(14))
            body.addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }

        val stats = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val s1 = card("مبيعات اليوم", "12,450", "ريال").also { stats.addView(it, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)) }
        val s2 = card("الأصناف", "145", "صنف مسجل").also {
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
            lp.setMargins(dp(8), 0, 0, 0)
            stats.addView(it, lp)
        }
        body.addView(stats)

        val cameraCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(18), dp(16), dp(18), dp(16))
            val title = TextView(this@MainActivity).apply {
                text = "كاميرات المراقبة"
                textSize = 18f
                setTextColor(textDark)
                setTypeface(typeface, android.graphics.Typeface.BOLD)
                gravity = Gravity.RIGHT
            }
            addView(title)
            val info = TextView(this@MainActivity).apply {
                text = if (cameras.isEmpty()) "لا توجد كاميرات مضافة — يمكنك إضافة كاميرات IP أو DVR/NVR عبر RTSP." else "تمت إضافة ${cameras.size} كاميرا مراقبة."
                textSize = 13f
                setTextColor(muted)
                gravity = Gravity.RIGHT
                setPadding(0, dp(7), 0, dp(10))
            }
            addView(info)
            val action = TextView(this@MainActivity).apply {
                text = "فتح كاميرات المراقبة  ›"
                textSize = 14f
                setTextColor(Color.WHITE)
                setBackgroundColor(blue)
                gravity = Gravity.CENTER
                setPadding(dp(12), dp(12), dp(12), dp(12))
                setOnClickListener { showCameras() }
            }
            addView(action)
        }
        val cameraLp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
        cameraLp.setMargins(0, dp(14), 0, 0)
        body.addView(cameraCard, cameraLp)

        val shortcuts = listOf("المبيعات", "المشتريات", "المخزون", "التقارير")
        TextView(this).apply {
            text = "الوصول السريع"
            textSize = 18f
            setTextColor(textDark)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            setPadding(0, dp(18), 0, dp(9))
            body.addView(this)
        }
        shortcuts.forEach { label ->
            TextView(this).apply {
                text = "  $label"
                textSize = 15f
                setTextColor(textDark)
                setBackgroundColor(Color.WHITE)
                gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
                setPadding(dp(16), dp(13), dp(16), dp(13))
                setOnClickListener { Toast.makeText(this@MainActivity, "سيتم فتح قسم $label ضمن النسخة المتكاملة", Toast.LENGTH_SHORT).show() }
                val lp = LinearLayout.LayoutParams(-1, dp(50))
                lp.setMargins(0, 0, 0, dp(7))
                body.addView(this, lp)
            }
        }
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(makeNav("الرئيسية"), LinearLayout.LayoutParams(-1, dp(70)))
        setContentView(root)
    }

    private fun showCameras() {
        releasePlayers()
        val root = baseRoot()
        root.addView(makeHeader("كاميرات المراقبة", "متابعة البث المباشر من الجوال"), LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        root.addView(makeTicker(), LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))

        val scroll = ScrollView(this)
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), dp(14), dp(14), dp(18))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        TextView(this).apply {
            text = "الكاميرات المضافة"
            textSize = 21f
            setTextColor(textDark)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            container.addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        if (cameras.isEmpty()) {
            val empty = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setPadding(dp(18), dp(55), dp(18), dp(35))
                TextView(this@MainActivity).apply {
                    text = "◉"
                    textSize = 54f
                    setTextColor(Color.rgb(75, 155, 225))
                    gravity = Gravity.CENTER
                    addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
                }
                TextView(this@MainActivity).apply {
                    text = "لا توجد كاميرات مضافة بعد"
                    textSize = 20f
                    setTextColor(textDark)
                    setTypeface(typeface, android.graphics.Typeface.BOLD)
                    gravity = Gravity.CENTER
                    setPadding(0, dp(10), 0, dp(6))
                    addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
                }
                TextView(this@MainActivity).apply {
                    text = "أضف كاميرا IP أو DVR/NVR باستخدام رابط RTSP."
                    textSize = 13f
                    setTextColor(muted)
                    gravity = Gravity.CENTER
                    addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
                }
            }
            container.addView(empty, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        } else {
            cameras.forEach { addCameraCard(it, container) }
        }
        scroll.addView(container)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))

        val add = TextView(this).apply {
            text = "+   إضافة كاميرا جديدة"
            textSize = 16f
            setTextColor(Color.WHITE)
            setBackgroundColor(blue)
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(13), dp(10), dp(13))
            setOnClickListener { showAddCameraDialog() }
        }
        root.addView(add, LinearLayout.LayoutParams(-1, dp(56)))
        root.addView(makeNav("الكاميرات"), LinearLayout.LayoutParams(-1, dp(70)))
        setContentView(root)
    }

    private fun addCameraCard(camera: CameraConfig, container: LinearLayout) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(10), dp(10), dp(10), dp(10))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        TextView(this).apply {
            text = "${camera.name}  •  ${camera.location}"
            textSize = 16f
            setTextColor(blue)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            setPadding(dp(4), dp(5), dp(4), dp(8))
            card.addView(this)
        }
        val playerView = PlayerView(this).apply {
            useController = true
            setBackgroundColor(Color.BLACK)
            layoutParams = LinearLayout.LayoutParams(-1, dp(220))
        }
        card.addView(playerView)
        val status = TextView(this).apply {
            text = "● جاري الاتصال بالكاميرا..."
            textSize = 12f
            setTextColor(Color.rgb(220, 130, 0))
            gravity = Gravity.RIGHT
            setPadding(dp(4), dp(8), dp(4), dp(6))
        }
        card.addView(status)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.RIGHT }
        val reconnect = TextView(this).apply {
            text = "إعادة الاتصال"
            textSize = 13f
            setTextColor(blue)
            setPadding(dp(14), dp(7), dp(14), dp(7))
            setOnClickListener { playCamera(camera, playerView, status) }
        }
        val remove = TextView(this).apply {
            text = "حذف"
            textSize = 13f
            setTextColor(Color.rgb(190, 45, 45))
            setPadding(dp(14), dp(7), dp(14), dp(7))
            setOnClickListener { cameras.remove(camera); saveCameras(); showCameras() }
        }
        actions.addView(remove); actions.addView(reconnect); card.addView(actions)
        val lp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.setMargins(0, 0, 0, dp(14))
        container.addView(card, lp)
        playCamera(camera, playerView, status)
    }

    private fun playCamera(camera: CameraConfig, view: PlayerView, status: TextView) {
        view.player?.release()
        val player = ExoPlayer.Builder(this).build()
        players.add(player)
        view.player = player
        player.setMediaItem(MediaItem.fromUri(Uri.parse(camera.rtspUrl)))
        player.addListener(object : Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                when (state) {
                    Player.STATE_BUFFERING -> { status.text = "● جاري تحميل بث ${camera.name}..."; status.setTextColor(Color.rgb(220, 130, 0)) }
                    Player.STATE_READY -> { status.text = "● الكاميرا متصلة ومباشرة"; status.setTextColor(Color.rgb(0, 150, 75)) }
                    Player.STATE_ENDED -> { status.text = "● انتهى البث"; status.setTextColor(Color.GRAY) }
                }
            }
            override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
                status.text = "● تعذر الاتصال: تحقق من رابط RTSP والشبكة"
                status.setTextColor(Color.rgb(200, 45, 45))
            }
        })
        player.prepare()
        player.playWhenReady = true
    }

    private fun showAddCameraDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(28), dp(6), dp(28), 0) }
        val name = EditText(this).apply { hint = "اسم الكاميرا"; setSingleLine(true) }
        val location = EditText(this).apply { hint = "الموقع - مثال: باب المحل"; setSingleLine(true) }
        val url = EditText(this).apply { hint = "رابط RTSP"; setSingleLine(false) }
        box.addView(name); box.addView(location); box.addView(url)
        AlertDialog.Builder(this)
            .setTitle("إضافة كاميرا مراقبة")
            .setMessage("يدعم التطبيق بث كاميرات IP وDVR/NVR عبر RTSP.")
            .setView(box)
            .setNegativeButton("إلغاء", null)
            .setPositiveButton("حفظ واتصال") { _, _ ->
                val n = name.text.toString().trim(); val l = location.text.toString().trim().ifEmpty { "المحل" }; val u = url.text.toString().trim()
                if (n.isEmpty() || u.isEmpty()) Toast.makeText(this, "أدخل اسم الكاميرا ورابط RTSP", Toast.LENGTH_LONG).show()
                else { cameras.add(CameraConfig(n, l, u)); saveCameras(); showCameras() }
            }.show()
    }

    private fun loadCameras() {
        cameras.clear()
        val raw = prefs.getString("items", "[]") ?: "[]"
        val array = JSONArray(raw)
        for (i in 0 until array.length()) {
            val o = array.getJSONObject(i)
            cameras.add(CameraConfig(o.getString("name"), o.getString("location"), o.getString("url")))
        }
    }

    private fun saveCameras() {
        val array = JSONArray()
        cameras.forEach { array.put(JSONObject().apply { put("name", it.name); put("location", it.location); put("url", it.rtspUrl) }) }
        prefs.edit().putString("items", array.toString()).apply()
    }

    private fun releasePlayers() {
        players.forEach { it.release() }
        players.clear()
    }

    override fun onDestroy() {
        releasePlayers()
        super.onDestroy()
    }
}

data class CameraConfig(val name: String, val location: String, val rtspUrl: String)

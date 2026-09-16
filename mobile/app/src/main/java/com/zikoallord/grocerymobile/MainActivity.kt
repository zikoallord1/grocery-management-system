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
import androidx.core.view.WindowCompat
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
    private val blueSoft = Color.rgb(232, 242, 252)
    private val bg = Color.rgb(246, 248, 252)
    private val textDark = Color.rgb(25, 52, 78)
    private val muted = Color.rgb(102, 116, 132)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        window.statusBarColor = blueDark
        window.navigationBarColor = Color.rgb(8, 28, 45)
        loadCameras()
        // Always start at the main dashboard. Cameras are a separate section.
        showHome()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun baseRoot(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        isFocusable = true
    }

    private fun makeHeader(title: String, subtitle: String = ""): LinearLayout {
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(blue)
            setPadding(dp(18), dp(12), dp(18), dp(12))
            gravity = Gravity.CENTER_VERTICAL
            minimumHeight = dp(70)
        }
        TextView(this).apply {
            text = title
            textSize = 21f
            setTextColor(Color.WHITE)
            gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            header.addView(this, LinearLayout.LayoutParams(-1, dp(30)))
        }
        if (subtitle.isNotEmpty()) {
            TextView(this).apply {
                text = subtitle
                textSize = 12f
                setTextColor(Color.rgb(225, 239, 255))
                gravity = Gravity.RIGHT
                header.addView(this, LinearLayout.LayoutParams(-1, dp(20)))
            }
        }
        return header
    }

    private fun makeTicker(): TextView = TextView(this).apply {
        text = "● المزامنة: جاهز   •   المبيعات اليوم: 12,450 ريال   •   تنبيهات المخزون: 3"
        textSize = 12f
        setTextColor(blue)
        setBackgroundColor(Color.WHITE)
        gravity = Gravity.CENTER
        setPadding(dp(8), dp(7), dp(8), dp(7))
        maxLines = 1
        ellipsize = android.text.TextUtils.TruncateAt.MARQUEE
        isSelected = true
        marqueeRepeatLimit = -1
    }

    private fun makeNav(active: String): LinearLayout {
        val nav = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(5), dp(5), dp(5), dp(5))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            elevation = dp(5).toFloat()
        }
        val items = listOf("الرئيسية", "المبيعات", "المخزون", "الكاميرات", "الإعدادات")
        items.forEach { label ->
            val button = TextView(this).apply {
                text = if (label == active) "●\n$label" else "○\n$label"
                textSize = 10f
                setTextColor(if (label == active) blue else muted)
                gravity = Gravity.CENTER
                setPadding(dp(2), dp(3), dp(2), dp(3))
                if (label == active) setBackgroundColor(blueSoft)
                setOnClickListener {
                    when (label) {
                        "الرئيسية" -> showHome()
                        "الكاميرات" -> showCameras()
                        else -> Toast.makeText(this@MainActivity, "قسم $label جاهز للربط في النسخة المتكاملة", Toast.LENGTH_SHORT).show()
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
        setPadding(dp(13), dp(12), dp(13), dp(12))
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        elevation = dp(1).toFloat()
        TextView(this@MainActivity).apply {
            text = title
            textSize = 12f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        TextView(this@MainActivity).apply {
            text = value
            textSize = 20f
            setTextColor(textDark)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            setPadding(0, dp(4), 0, dp(1))
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
        TextView(this@MainActivity).apply {
            text = hint
            textSize = 10f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            addView(this, LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT))
        }
    }

    private fun sectionTitle(text: String): TextView = TextView(this).apply {
        this.text = text
        textSize = 18f
        setTextColor(textDark)
        setTypeface(typeface, android.graphics.Typeface.BOLD)
        gravity = Gravity.RIGHT
    }

    private fun actionRow(label: String, onClick: () -> Unit): TextView = TextView(this).apply {
        text = label
        textSize = 14f
        setTextColor(textDark)
        setBackgroundColor(Color.WHITE)
        gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
        setPadding(dp(15), dp(12), dp(15), dp(12))
        setOnClickListener { onClick() }
        elevation = dp(1).toFloat()
    }

    private fun showHome() {
        releasePlayers()
        val root = baseRoot()
        root.addView(makeHeader("نظام البقالة المحاسبي", "لوحة التحكم وإدارة المتجر"))
        root.addView(makeTicker())

        val scroll = ScrollView(this)
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(14), dp(12), dp(16))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        body.addView(sectionTitle("لوحة المتابعة"), LinearLayout.LayoutParams(-1, dp(32)))
        TextView(this).apply {
            text = "مرحبًا بك — اختر القسم الذي تريد إدارته"
            textSize = 13f
            setTextColor(muted)
            gravity = Gravity.RIGHT
            setPadding(0, 0, 0, dp(10))
            body.addView(this, LinearLayout.LayoutParams(-1, dp(30)))
        }

        val stats = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        stats.addView(card("مبيعات اليوم", "12,450", "ريال"), LinearLayout.LayoutParams(0, dp(105), 1f))
        val p = LinearLayout.LayoutParams(0, dp(105), 1f)
        p.setMargins(dp(7), 0, 0, 0)
        stats.addView(card("الأصناف", "145", "صنف مسجل"), p)
        body.addView(stats)

        val cameraCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(16), dp(14), dp(16), dp(14))
            elevation = dp(1).toFloat()
            addView(sectionTitle("كاميرات المراقبة"), LinearLayout.LayoutParams(-1, dp(30)))
            TextView(this@MainActivity).apply {
                text = if (cameras.isEmpty()) "لا توجد كاميرات مضافة حاليًا" else "تمت إضافة ${cameras.size} كاميرا مراقبة"
                textSize = 12f
                setTextColor(muted)
                gravity = Gravity.RIGHT
                setPadding(0, dp(3), 0, dp(9))
                addView(this, LinearLayout.LayoutParams(-1, dp(32)))
            }
            TextView(this@MainActivity).apply {
                text = "فتح كاميرات المراقبة  ›"
                textSize = 14f
                setTextColor(Color.WHITE)
                setBackgroundColor(blue)
                gravity = Gravity.CENTER
                setPadding(dp(10), dp(10), dp(10), dp(10))
                setOnClickListener { showCameras() }
                addView(this, LinearLayout.LayoutParams(-1, dp(46)))
            }
        }
        val cameraLp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
        cameraLp.setMargins(0, dp(12), 0, 0)
        body.addView(cameraCard, cameraLp)

        body.addView(sectionTitle("الوصول السريع"), LinearLayout.LayoutParams(-1, dp(34)).apply { topMargin = dp(14) })
        listOf("المبيعات", "المشتريات", "المخزون", "التقارير").forEach { label ->
            val row = actionRow("$label    ›") { Toast.makeText(this, "فتح قسم $label", Toast.LENGTH_SHORT).show() }
            val lp = LinearLayout.LayoutParams(-1, dp(48))
            lp.setMargins(0, 0, 0, dp(6))
            body.addView(row, lp)
        }
        scroll.addView(body)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(makeNav("الرئيسية"), LinearLayout.LayoutParams(-1, dp(68)))
        setContentView(root)
    }

    private fun showCameras() {
        releasePlayers()
        val root = baseRoot()
        root.addView(makeHeader("كاميرات المراقبة", "متابعة البث المباشر من الجوال"))
        root.addView(makeTicker())

        val scroll = ScrollView(this)
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(14), dp(12), dp(14))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        container.addView(sectionTitle("الكاميرات المضافة"), LinearLayout.LayoutParams(-1, dp(34)))
        if (cameras.isEmpty()) {
            val empty = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                gravity = Gravity.CENTER
                setBackgroundColor(Color.WHITE)
                setPadding(dp(18), dp(45), dp(18), dp(35))
                TextView(this@MainActivity).apply {
                    text = "◉"
                    textSize = 48f
                    setTextColor(blue)
                    gravity = Gravity.CENTER
                    addView(this, LinearLayout.LayoutParams(-1, dp(60)))
                }
                TextView(this@MainActivity).apply {
                    text = "لا توجد كاميرات مضافة بعد"
                    textSize = 18f
                    setTextColor(textDark)
                    setTypeface(typeface, android.graphics.Typeface.BOLD)
                    gravity = Gravity.CENTER
                    setPadding(0, dp(7), 0, dp(5))
                    addView(this, LinearLayout.LayoutParams(-1, dp(34)))
                }
                TextView(this@MainActivity).apply {
                    text = "أضف كاميرا IP أو DVR/NVR باستخدام رابط RTSP."
                    textSize = 12f
                    setTextColor(muted)
                    gravity = Gravity.CENTER
                    addView(this, LinearLayout.LayoutParams(-1, dp(30)))
                }
            }
            val lp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
            lp.setMargins(0, dp(8), 0, 0)
            container.addView(empty, lp)
        } else {
            cameras.forEach { addCameraCard(it, container) }
        }
        scroll.addView(container)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        val add = TextView(this).apply {
            text = "+   إضافة كاميرا جديدة"
            textSize = 15f
            setTextColor(Color.WHITE)
            setBackgroundColor(blue)
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(10), dp(10), dp(10))
            setOnClickListener { showAddCameraDialog() }
        }
        root.addView(add, LinearLayout.LayoutParams(-1, dp(52)))
        root.addView(makeNav("الكاميرات"), LinearLayout.LayoutParams(-1, dp(68)))
        setContentView(root)
    }

    private fun addCameraCard(camera: CameraConfig, container: LinearLayout) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(10), dp(10), dp(10), dp(10))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            elevation = dp(1).toFloat()
        }
        TextView(this).apply {
            text = "${camera.name}  •  ${camera.location}"
            textSize = 15f
            setTextColor(blue)
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.RIGHT
            setPadding(dp(4), dp(4), dp(4), dp(7))
            card.addView(this, LinearLayout.LayoutParams(-1, dp(34)))
        }
        val playerView = PlayerView(this).apply {
            useController = true
            setBackgroundColor(Color.BLACK)
            layoutParams = LinearLayout.LayoutParams(-1, dp(210))
        }
        card.addView(playerView)
        val status = TextView(this).apply {
            text = "● جاري الاتصال بالكاميرا..."
            textSize = 11f
            setTextColor(Color.rgb(220, 130, 0))
            gravity = Gravity.RIGHT
            setPadding(dp(4), dp(7), dp(4), dp(4))
        }
        card.addView(status, LinearLayout.LayoutParams(-1, dp(30)))
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.RIGHT; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        val reconnect = TextView(this).apply {
            text = "إعادة الاتصال"
            textSize = 12f
            setTextColor(blue)
            setPadding(dp(12), dp(6), dp(12), dp(6))
            setOnClickListener { playCamera(camera, playerView, status) }
        }
        val remove = TextView(this).apply {
            text = "حذف"
            textSize = 12f
            setTextColor(Color.rgb(190, 45, 45))
            setPadding(dp(12), dp(6), dp(12), dp(6))
            setOnClickListener { cameras.remove(camera); saveCameras(); showCameras() }
        }
        actions.addView(remove); actions.addView(reconnect); card.addView(actions, LinearLayout.LayoutParams(-1, dp(38)))
        val lp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.setMargins(0, 0, 0, dp(12))
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
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(24), dp(6), dp(24), 0); layoutDirection = View.LAYOUT_DIRECTION_RTL }
        val name = EditText(this).apply { hint = "اسم الكاميرا"; setSingleLine(true); textSize = 15f }
        val location = EditText(this).apply { hint = "الموقع - مثال: باب المحل"; setSingleLine(true); textSize = 15f }
        val url = EditText(this).apply { hint = "رابط RTSP"; setSingleLine(false); textSize = 15f }
        box.addView(name, LinearLayout.LayoutParams(-1, dp(52)))
        box.addView(location, LinearLayout.LayoutParams(-1, dp(52)))
        box.addView(url, LinearLayout.LayoutParams(-1, dp(70)))
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
        try {
            val array = JSONArray(raw)
            for (i in 0 until array.length()) {
                val o = array.getJSONObject(i)
                cameras.add(CameraConfig(o.getString("name"), o.getString("location"), o.getString("url")))
            }
        } catch (_: Exception) { cameras.clear() }
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

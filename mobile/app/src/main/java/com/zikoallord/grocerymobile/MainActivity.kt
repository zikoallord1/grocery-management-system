package com.zikoallord.grocerymobile

import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.Gravity
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
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : AppCompatActivity() {
    private val cameras = mutableListOf<CameraConfig>()
    private val players = mutableListOf<ExoPlayer>()
    private lateinit var cameraContainer: LinearLayout
    private lateinit var syncStatus: TextView
    private lateinit var summary: TextView
    private val prefs by lazy { getSharedPreferences("mobile", MODE_PRIVATE) }
    private val cameraPrefs by lazy { getSharedPreferences("cameras", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        loadCameras()
        buildUi()
        refreshFromDesktop()
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(244, 247, 251))
            layoutDirection = LinearLayout.LAYOUT_DIRECTION_RTL
        }
        val header = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setBackgroundColor(Color.rgb(5, 67, 125))
            setPadding(18, 12, 18, 12)
            layoutDirection = LinearLayout.LAYOUT_DIRECTION_RTL
        }
        val title = TextView(this).apply {
            text = "نظام البقالة المحاسبي\nالمتابعة من الجوال"
            textSize = 19f
            setTextColor(Color.WHITE)
        }
        header.addView(title, LinearLayout.LayoutParams(0, -2, 1f))
        val settings = TextView(this).apply {
            text = "⚙ الاتصال"
            textSize = 14f
            setTextColor(Color.WHITE)
            setPadding(14, 12, 14, 12)
            setOnClickListener { showServerDialog() }
        }
        header.addView(settings)
        root.addView(header)

        syncStatus = TextView(this).apply {
            text = "● لم تتم المزامنة بعد"
            textSize = 13f
            setTextColor(Color.DKGRAY)
            setPadding(16, 10, 16, 10)
            gravity = Gravity.CENTER
        }
        root.addView(syncStatus, LinearLayout.LayoutParams(-1, 46))

        summary = TextView(this).apply {
            text = "بيانات النظام ستظهر هنا عند الاتصال بجهاز البقالة."
            textSize = 15f
            setTextColor(Color.rgb(20, 45, 70))
            setBackgroundColor(Color.WHITE)
            setPadding(18, 16, 18, 16)
            gravity = Gravity.RIGHT
        }
        root.addView(summary, LinearLayout.LayoutParams(-1, -2))

        val scroll = ScrollView(this)
        cameraContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(14, 14, 14, 28)
            layoutDirection = LinearLayout.LAYOUT_DIRECTION_RTL
        }
        scroll.addView(cameraContainer)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))

        val add = TextView(this).apply {
            text = "+  إضافة كاميرا مراقبة"
            textSize = 17f
            setTextColor(Color.WHITE)
            setBackgroundColor(Color.rgb(0, 119, 204))
            gravity = Gravity.CENTER
            setPadding(10, 16, 10, 16)
            setOnClickListener { showAddCameraDialog() }
        }
        root.addView(add, LinearLayout.LayoutParams(-1, 58))

        val nav = TextView(this).apply {
            text = "الرئيسية     المبيعات     المخزون     التقارير     الكاميرات"
            textSize = 12f
            setTextColor(Color.DKGRAY)
            setBackgroundColor(Color.WHITE)
            gravity = Gravity.CENTER
            setPadding(4, 12, 4, 12)
        }
        root.addView(nav, LinearLayout.LayoutParams(-1, 48))
        setContentView(root)
        renderCameras()
    }

    private fun serverUrl(): String = prefs.getString("server_url", "")?.trim()?.trimEnd('/') ?: ""

    private fun showServerDialog() {
        val input = EditText(this).apply {
            hint = "http://192.168.1.20:8765"
            setSingleLine(true)
            setText(serverUrl())
        }
        AlertDialog.Builder(this)
            .setTitle("اتصال بنظام البقالة")
            .setMessage("أدخل عنوان جهاز Windows الذي يشغل النظام، ثم اضغط اتصال. يجب أن يكون الهاتف والكمبيوتر على نفس الشبكة المحلية.")
            .setView(input)
            .setNegativeButton("إلغاء", null)
            .setPositiveButton("حفظ واختبار") { _, _ ->
                val value = input.text.toString().trim().trimEnd('/')
                if (value.isEmpty()) {
                    prefs.edit().remove("server_url").apply()
                    syncStatus.text = "● لم يتم تحديد جهاز النظام"
                } else {
                    prefs.edit().putString("server_url", value).apply()
                    refreshFromDesktop()
                }
            }
            .show()
    }

    private fun refreshFromDesktop() {
        val base = serverUrl()
        if (base.isEmpty()) {
            syncStatus.text = "● أدخل عنوان جهاز البقالة من زر ⚙ الاتصال"
            return
        }
        syncStatus.text = "● جاري المزامنة مع جهاز البقالة..."
        Thread {
            try {
                val connection = URL("$base/api/mobile/summary").openConnection() as HttpURLConnection
                connection.requestMethod = "GET"
                connection.connectTimeout = 5000
                connection.readTimeout = 7000
                val response = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
                connection.disconnect()
                val data = JSONObject(response)
                runOnUiThread {
                    if (data.optBoolean("ok")) {
                        summary.text = "مبيعات اليوم: ${money(data.optDouble("sales"))}    |    مشتريات: ${money(data.optDouble("purchases"))}\n" +
                            "المصروفات: ${money(data.optDouble("expenses"))}    |    صافي الربح: ${money(data.optDouble("profit"))}\n" +
                            "ذمم العملاء: ${money(data.optDouble("receivables"))}    |    ذمم الموردين: ${money(data.optDouble("payables"))}\n" +
                            "الصندوق: ${money(data.optDouble("cash"))}    |    أصناف منخفضة: ${data.optInt("low_stock")}"
                        syncStatus.text = "● متصل بالمزامنة — ${data.optString("date")}" 
                        syncStatus.setTextColor(Color.rgb(0, 145, 75))
                    } else {
                        syncStatus.text = "● تعذر قراءة بيانات النظام"
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    syncStatus.text = "● غير متصل — تحقق من عنوان الجهاز والشبكة"
                    syncStatus.setTextColor(Color.rgb(190, 45, 45))
                }
            }
        }.start()
    }

    private fun money(value: Double): String = String.format("%,.2f", value)

    private fun renderCameras() {
        players.forEach { it.release() }
        players.clear()
        cameraContainer.removeAllViews()
        val title = TextView(this).apply {
            text = "كاميرات المراقبة"
            textSize = 21f
            setTextColor(Color.rgb(20, 45, 70))
            setPadding(4, 4, 4, 14)
            gravity = Gravity.RIGHT
        }
        cameraContainer.addView(title)
        if (cameras.isEmpty()) {
            val empty = TextView(this).apply {
                text = "لا توجد كاميرات مضافة بعد\nأضف كاميرا IP أو DVR/NVR باستخدام رابط RTSP."
                textSize = 16f
                gravity = Gravity.CENTER
                setTextColor(Color.GRAY)
                setPadding(20, 50, 20, 50)
            }
            cameraContainer.addView(empty)
            return
        }
        cameras.forEach { camera -> addCameraCard(camera) }
    }

    private fun addCameraCard(camera: CameraConfig) {
        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(10, 10, 10, 10)
            layoutDirection = LinearLayout.LAYOUT_DIRECTION_RTL
        }
        val title = TextView(this).apply {
            text = "${camera.name}    •    ${camera.location}"
            textSize = 16f
            setTextColor(Color.rgb(0, 70, 125))
            setPadding(4, 6, 4, 8)
        }
        card.addView(title)
        val playerView = PlayerView(this).apply {
            useController = true
            setBackgroundColor(Color.BLACK)
            layoutParams = LinearLayout.LayoutParams(-1, 220)
        }
        card.addView(playerView)
        val status = TextView(this).apply {
            text = "● جاري الاتصال بالكاميرا..."
            textSize = 12f
            setTextColor(Color.rgb(220, 130, 0))
            setPadding(4, 8, 4, 6)
        }
        card.addView(status)
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.RIGHT }
        val reconnect = TextView(this).apply {
            text = "إعادة الاتصال"
            setTextColor(Color.rgb(0, 95, 180))
            setPadding(18, 8, 18, 8)
            setOnClickListener { playCamera(camera, playerView, status) }
        }
        val remove = TextView(this).apply {
            text = "حذف"
            setTextColor(Color.rgb(190, 45, 45))
            setPadding(18, 8, 18, 8)
            setOnClickListener { cameras.remove(camera); saveCameras(); renderCameras() }
        }
        actions.addView(remove)
        actions.addView(reconnect)
        card.addView(actions)
        val lp = LinearLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT)
        lp.setMargins(0, 0, 0, 18)
        cameraContainer.addView(card, lp)
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
                    Player.STATE_BUFFERING -> status.text = "● جاري تحميل بث ${camera.name}..."
                    Player.STATE_READY -> status.text = "● الكاميرا متصلة ومباشرة"
                    Player.STATE_ENDED -> status.text = "● انتهى البث"
                }
            }
            override fun onPlayerError(error: androidx.media3.common.PlaybackException) {
                status.text = "● تعذر الاتصال: تحقق من رابط RTSP والشبكة"
            }
        })
        player.prepare()
        player.playWhenReady = true
    }

    private fun showAddCameraDialog() {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(36, 10, 36, 0) }
        val name = EditText(this).apply { hint = "اسم الكاميرا" }
        val location = EditText(this).apply { hint = "الموقع - مثال: باب المحل" }
        val url = EditText(this).apply { hint = "رابط RTSP"; setSingleLine(true) }
        box.addView(name); box.addView(location); box.addView(url)
        AlertDialog.Builder(this)
            .setTitle("إضافة كاميرا مراقبة")
            .setView(box)
            .setNegativeButton("إلغاء", null)
            .setPositiveButton("حفظ واتصال") { _, _ ->
                val n = name.text.toString().trim()
                val l = location.text.toString().trim().ifEmpty { "المحل" }
                val u = url.text.toString().trim()
                if (n.isEmpty() || u.isEmpty()) Toast.makeText(this, "أدخل اسم الكاميرا ورابط RTSP", Toast.LENGTH_LONG).show()
                else { cameras.add(CameraConfig(n, l, u)); saveCameras(); renderCameras() }
            }
            .show()
    }

    private fun loadCameras() {
        cameras.clear()
        val raw = cameraPrefs.getString("items", "[]") ?: "[]"
        val array = JSONArray(raw)
        for (i in 0 until array.length()) {
            val o = array.getJSONObject(i)
            cameras.add(CameraConfig(o.getString("name"), o.getString("location"), o.getString("url")))
        }
    }

    private fun saveCameras() {
        val array = JSONArray()
        cameras.forEach { array.put(JSONObject().apply { put("name", it.name); put("location", it.location); put("url", it.rtspUrl) }) }
        cameraPrefs.edit().putString("items", array.toString()).apply()
    }

    override fun onDestroy() {
        players.forEach { it.release() }
        players.clear()
        super.onDestroy()
    }
}

data class CameraConfig(val name: String, val location: String, val rtspUrl: String)

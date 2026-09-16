package com.zikoallord.grocerymobile

import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat

class MainActivity : AppCompatActivity() {
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
        showHome()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun baseRoot() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        isFocusable = true
    }

    private fun makeHeader(title: String, subtitle: String = "") = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(blue)
        setPadding(dp(18), dp(12), dp(18), dp(12))
        gravity = Gravity.CENTER_VERTICAL
        minimumHeight = dp(70)
        TextView(this@MainActivity).apply {
            text = title
            textSize = 21f
            setTextColor(Color.WHITE)
            gravity = Gravity.RIGHT or Gravity.CENTER_VERTICAL
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            addView(this, LinearLayout.LayoutParams(-1, dp(30)))
        }
        if (subtitle.isNotEmpty()) {
            TextView(this@MainActivity).apply {
                text = subtitle
                textSize = 12f
                setTextColor(Color.rgb(225, 239, 255))
                gravity = Gravity.RIGHT
                addView(this, LinearLayout.LayoutParams(-1, dp(20)))
            }
        }
    }

    private fun makeTicker() = TextView(this).apply {
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

    private fun makeNav(active: String) = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        setBackgroundColor(Color.WHITE)
        setPadding(dp(5), dp(5), dp(5), dp(5))
        layoutDirection = View.LAYOUT_DIRECTION_RTL
        elevation = dp(5).toFloat()
        listOf("الرئيسية", "المبيعات", "المخزون", "الإعدادات").forEach { label ->
            val button = TextView(this@MainActivity).apply {
                text = if (label == active) "●\n$label" else "○\n$label"
                textSize = 10f
                setTextColor(if (label == active) blue else muted)
                gravity = Gravity.CENTER
                setPadding(dp(2), dp(3), dp(2), dp(3))
                if (label == active) setBackgroundColor(blueSoft)
                setOnClickListener {
                    if (label == "الرئيسية") showHome()
                    else Toast.makeText(this@MainActivity, "قسم $label جاهز للربط في النسخة المتكاملة", Toast.LENGTH_SHORT).show()
                }
            }
            addView(button, LinearLayout.LayoutParams(0, dp(58), 1f))
        }
    }

    private fun card(title: String, value: String, hint: String) = LinearLayout(this).apply {
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

    private fun sectionTitle(text: String) = TextView(this).apply {
        this.text = text
        textSize = 18f
        setTextColor(textDark)
        setTypeface(typeface, android.graphics.Typeface.BOLD)
        gravity = Gravity.RIGHT
    }

    private fun actionRow(label: String, onClick: () -> Unit) = TextView(this).apply {
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
}

package com.zikoallord.grocerymobile

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat

class MainActivity : AppCompatActivity() {
    private val blue = Color.rgb(8, 113, 232)
    private val blueDark = Color.rgb(4, 48, 94)
    private val blueHeader = Color.rgb(5, 72, 132)
    private val blueSoft = Color.rgb(235, 245, 255)
    private val bg = Color.rgb(245, 249, 253)
    private val white = Color.WHITE
    private val text = Color.rgb(13, 55, 101)
    private val muted = Color.rgb(92, 113, 136)
    private val green = Color.rgb(18, 177, 112)
    private val orange = Color.rgb(246, 132, 12)
    private val purple = Color.rgb(103, 70, 215)
    private val red = Color.rgb(235, 53, 68)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        window.statusBarColor = blueDark
        window.navigationBarColor = blueDark
        showHome()
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun tv(label: String, size: Float, color: Int = text, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = label
            textSize = size
            setTextColor(color)
            gravity = Gravity.CENTER_VERTICAL or Gravity.RIGHT
            if (bold) setTypeface(typeface, Typeface.BOLD)
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }

    private fun root() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        layoutDirection = View.LAYOUT_DIRECTION_RTL
    }

    private fun header(title: String = "نظام البقالة المحاسبي", subtitle: String = "إدارة شاملة .. لمتجرك بكل سهولة"): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(blueHeader)
            setPadding(dp(12), dp(9), dp(12), dp(9))
            gravity = Gravity.CENTER_VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val menu = tv("☰", 22f, white, true).apply { gravity = Gravity.CENTER; setPadding(dp(7), 0, dp(7), 0) }
        box.addView(menu, LinearLayout.LayoutParams(dp(38), dp(52)))
        val brand = tv("▣", 26f, white, true).apply {
            gravity = Gravity.CENTER
            setBackgroundColor(blue)
        }
        box.addView(brand, LinearLayout.LayoutParams(dp(52), dp(52)))
        val names = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(9), 0, 0, 0) }
        names.addView(tv(title, 19f, white, true), LinearLayout.LayoutParams(-1, dp(28)))
        names.addView(tv(subtitle, 11f, Color.rgb(220, 238, 255)), LinearLayout.LayoutParams(-1, dp(20)))
        box.addView(names, LinearLayout.LayoutParams(0, dp(55), 1f))
        box.addView(tv("◉", 23f, white, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(38), dp(52)))
        return box
    }

    private fun ticker(): View = tv("✓  تم استلام دفعة من المورد 8,320 ريال     ⚠  المخزون منخفض على بعض الأصناف     ✓  تم تسجيل عملية بيع جديدة بقيمة 12,450 ريال", 11f, white, true).apply {
        setBackgroundColor(blue)
        gravity = Gravity.CENTER
        setPadding(dp(7), dp(5), dp(7), dp(5))
        maxLines = 1
        ellipsize = TextUtils.TruncateAt.MARQUEE
        isSelected = true
        marqueeRepeatLimit = -1
    }

    private fun bottomNav(active: String): View {
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(white)
            elevation = dp(8).toFloat()
            setPadding(dp(3), dp(3), dp(3), dp(3))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val items = listOf("الرئيسية", "المبيعات", "المخزون", "الكاميرات", "المزيد")
        items.forEach { name ->
            val b = tv(if (name == active) "●\n$name" else "○\n$name", 10f, if (name == active) blue else muted, name == active).apply {
                gravity = Gravity.CENTER
                setPadding(0, dp(3), 0, dp(2))
                if (name == active) setBackgroundColor(blueSoft)
                setOnClickListener {
                    when (name) {
                        "الرئيسية" -> showHome()
                        "المبيعات" -> showSales()
                        "المخزون" -> showInventory()
                        "الكاميرات" -> showCameras()
                        else -> showMore()
                    }
                }
            }
            bar.addView(b, LinearLayout.LayoutParams(0, dp(62), 1f))
        }
        return bar
    }

    private fun card(title: String, value: String, tone: Int, icon: String): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(white)
            setPadding(dp(11), dp(8), dp(11), dp(8))
            elevation = dp(2).toFloat()
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val top = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        top.addView(tv(title, 11f, text, true), LinearLayout.LayoutParams(0, dp(25), 1f))
        top.addView(tv(icon, 20f, tone, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(28), dp(25)))
        box.addView(top)
        box.addView(tv(value, 21f, tone, true), LinearLayout.LayoutParams(-1, dp(32)))
        box.addView(tv("ريال", 10f, muted), LinearLayout.LayoutParams(-1, dp(17)))
        return box
    }

    private fun section(title: String): TextView = tv(title, 17f, text, true).apply { setPadding(0, dp(4), 0, dp(5)) }

    private fun button(label: String, action: () -> Unit, fill: Int = white): TextView = tv(label, 13f, if (fill == white) blue else white, true).apply {
        setBackgroundColor(fill)
        gravity = Gravity.CENTER
        setPadding(dp(8), dp(8), dp(8), dp(8))
        elevation = dp(1).toFloat()
        setOnClickListener { action() }
    }

    private fun row(label: String, value: String = "", action: (() -> Unit)? = null): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(white)
            setPadding(dp(10), dp(7), dp(10), dp(7))
            gravity = Gravity.CENTER_VERTICAL
            elevation = dp(1).toFloat()
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        box.addView(tv(label, 12f, text, true), LinearLayout.LayoutParams(0, dp(42), 1f))
        if (value.isNotEmpty()) box.addView(tv(value, 11f, muted), LinearLayout.LayoutParams(dp(100), dp(42)))
        box.addView(tv("›", 22f, blue, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(28), dp(42)))
        if (action != null) box.setOnClickListener { action() }
        return box
    }

    private fun bodyContainer(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(12), dp(10), dp(12), dp(12))
        layoutDirection = View.LAYOUT_DIRECTION_RTL
    }

    private fun finish(root: LinearLayout, active: String) {
        root.addView(bottomNav(active), LinearLayout.LayoutParams(-1, dp(68)))
        setContentView(root)
    }

    private fun showHome() {
        val r = root()
        r.addView(header())
        r.addView(ticker(), LinearLayout.LayoutParams(-1, dp(34)))
        val scroll = ScrollView(this)
        val b = bodyContainer()
        b.addView(section("لوحة التحكم  |  الفرع الرئيسي"), LinearLayout.LayoutParams(-1, dp(38)))
        b.addView(tv("مرحبًا بك — اختر القسم الذي تريد إدارته", 12f, muted), LinearLayout.LayoutParams(-1, dp(27)))

        val stats1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        stats1.addView(card("المبيعات اليوم", "12,450", green, "▥"), LinearLayout.LayoutParams(0, dp(106), 1f))
        val sp = LinearLayout.LayoutParams(0, dp(106), 1f); sp.setMargins(dp(7), 0, 0, 0)
        stats1.addView(card("المشتريات اليوم", "8,320", blue, "🛒"), sp)
        b.addView(stats1)

        val stats2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL; setPadding(0, dp(7), 0, 0) }
        stats2.addView(card("المخزون الحالي", "145", orange, "▣"), LinearLayout.LayoutParams(0, dp(106), 1f))
        val sp2 = LinearLayout.LayoutParams(0, dp(106), 1f); sp2.setMargins(dp(7), 0, 0, 0)
        stats2.addView(card("الأرباح اليوم", "4,130", purple, "↗"), sp2)
        b.addView(stats2)

        b.addView(section("أحدث العمليات"), LinearLayout.LayoutParams(-1, dp(37)).apply { topMargin = dp(10) })
        listOf("مبيعات" to "2,350 ريال", "شراء من المورد" to "4,800 ريال", "إضافة مخزون" to "1,250 ريال", "مصروفات تشغيلية" to "650 ريال").forEach { (a, v) ->
            b.addView(row(a, v), LinearLayout.LayoutParams(-1, dp(49)).apply { bottomMargin = dp(5) })
        }

        b.addView(section("العمليات السريعة"), LinearLayout.LayoutParams(-1, dp(37)).apply { topMargin = dp(8) })
        val q = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        q.addView(button("＋ مبيعات جديدة", { showSales() }, blue), LinearLayout.LayoutParams(0, dp(49), 1f))
        q.addView(button("＋ مشتريات", { toast("فتح المشتريات") }), LinearLayout.LayoutParams(0, dp(49), 1f).apply { marginStart = dp(6) })
        b.addView(q)
        val q2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL; setPadding(0, dp(6), 0, 0) }
        q2.addView(button("＋ إضافة صنف", { showInventory() }), LinearLayout.LayoutParams(0, dp(49), 1f))
        q2.addView(button("▥ تقرير سريع", { showReports() }), LinearLayout.LayoutParams(0, dp(49), 1f).apply { marginStart = dp(6) })
        b.addView(q2)
        scroll.addView(b)
        r.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        finish(r, "الرئيسية")
    }

    private fun pageRoot(title: String, subtitle: String): Pair<LinearLayout, LinearLayout> {
        val r = root(); r.addView(header(title, subtitle)); r.addView(ticker(), LinearLayout.LayoutParams(-1, dp(34)))
        val scroll = ScrollView(this); val b = bodyContainer(); scroll.addView(b); r.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f)); return Pair(r, b)
    }

    private fun showSales() {
        val (r, b) = pageRoot("المبيعات", "فاتورة بيع جديدة وإدارة المبيعات")
        val tabs = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val t = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        listOf("بيع جديد", "الفواتير", "الطلبات").forEach { x -> t.addView(button(x, { toast(x) }, if (x == "بيع جديد") blue else white), LinearLayout.LayoutParams(dp(105), dp(42)).apply { marginStart = dp(5) }) }
        tabs.addView(t); b.addView(tabs, LinearLayout.LayoutParams(-1, dp(48)))
        b.addView(row("🔎  ابحث عن صنف بالاسم أو الباركود..."), LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(7) })
        listOf("مياه معدنية" to "120 متوفر   0.50 ريال", "شاي" to "85 متوفر   1.25 ريال", "سكر" to "60 متوفر   2.00 ريال", "زيت نباتي" to "45 متوفر   3.50 ريال", "أرز" to "30 متوفر   7.50 ريال").forEach { (n, v) ->
            b.addView(row(n, v) { toast("إضافة $n إلى الفاتورة") }, LinearLayout.LayoutParams(-1, dp(54)).apply { bottomMargin = dp(5) })
        }
        b.addView(section("إجمالي الفاتورة"), LinearLayout.LayoutParams(-1, dp(36)).apply { topMargin = dp(8) })
        b.addView(tv("0.00 ريال", 24f, green, true).apply { setBackgroundColor(white); gravity = Gravity.CENTER; setPadding(0, dp(8), 0, dp(8)) }, LinearLayout.LayoutParams(-1, dp(54)))
        finish(r, "المبيعات")
    }

    private fun showInventory() {
        val (r, b) = pageRoot("المخزون", "إدارة الأصناف والكميات والأسعار والباركود")
        b.addView(row("🔎  ابحث عن صنف..."), LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(8) })
        val filters = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val f = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        listOf("جميع الأصناف", "الأكثر مبيعًا", "الأقل مخزونًا", "حسب الكمية").forEach { x -> f.addView(button(x, { toast(x) }, if (x == "جميع الأصناف") blue else white), LinearLayout.LayoutParams(dp(112), dp(42)).apply { marginStart = dp(5) }) }
        filters.addView(f); b.addView(filters, LinearLayout.LayoutParams(-1, dp(48)))
        listOf("مياه معدنية" to "120   شراء 0.35   بيع 0.50", "شاي" to "85   شراء 0.90   بيع 1.25", "سكر" to "60   شراء 1.50   بيع 2.00", "زيت نباتي" to "45   شراء 2.80   بيع 4.00", "أرز" to "30   شراء 4.50   بيع 7.50", "دقيق" to "50   شراء 0.80   بيع 3.00").forEach { (n, v) -> b.addView(row(n, v), LinearLayout.LayoutParams(-1, dp(55)).apply { bottomMargin = dp(5) }) }
        b.addView(tv("إجمالي المخزون    7,190 ريال", 15f, green, true).apply { setBackgroundColor(Color.rgb(231, 250, 242)); gravity = Gravity.CENTER; setPadding(0, dp(10), 0, dp(10)) }, LinearLayout.LayoutParams(-1, dp(48)))
        finish(r, "المخزون")
    }

    private fun showCameras() {
        val (r, b) = pageRoot("مراقبة الكاميرات", "متابعة الكاميرات من داخل نظام البقالة")
        val filter = HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false }
        val ft = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        listOf("جميع الكاميرات", "متصلة", "غير متصلة").forEach { x -> ft.addView(button(x, { toast(x) }, if (x == "جميع الكاميرات") blue else white), LinearLayout.LayoutParams(dp(112), dp(42)).apply { marginStart = dp(5) }) }
        filter.addView(ft); b.addView(filter, LinearLayout.LayoutParams(-1, dp(48)))
        listOf("الكاميرا 1" to "مدخل المحل", "الكاميرا 2" to "قسم المواد الغذائية", "الكاميرا 3" to "المخزن", "الكاميرا 4" to "صالة البيع", "الكاميرا 5" to "المحاسبة").forEach { (name, place) ->
            val c = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setBackgroundColor(white); setPadding(dp(10), dp(7), dp(10), dp(7)); gravity = Gravity.CENTER_VERTICAL; layoutDirection = View.LAYOUT_DIRECTION_RTL; elevation = dp(1).toFloat() }
            c.addView(tv("▣", 27f, blue, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(48), dp(48)))
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(8), 0, 0, 0) }
            info.addView(tv(name, 13f, text, true), LinearLayout.LayoutParams(-1, dp(25)))
            info.addView(tv("● متصلة  •  $place", 10f, green), LinearLayout.LayoutParams(-1, dp(21)))
            c.addView(info, LinearLayout.LayoutParams(0, dp(55), 1f)); b.addView(c, LinearLayout.LayoutParams(-1, dp(64)).apply { bottomMargin = dp(6) })
        }
        b.addView(button("＋ إضافة كاميرا", { toast("إضافة كاميرا") }, blue), LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(5) })
        finish(r, "الكاميرات")
    }

    private fun showReports() {
        val (r, b) = pageRoot("التقارير", "تقارير المبيعات والمخزون والمالية")
        listOf("تقرير المبيعات اليومية", "تقرير الأصناف الأكثر مبيعًا", "تقرير المخزون المنخفض", "تقرير العملاء", "تقرير المشتريات", "التقرير المالي").forEach { x -> b.addView(row(x) { toast("فتح $x") }, LinearLayout.LayoutParams(-1, dp(53)).apply { bottomMargin = dp(6) }) }
        finish(r, "المزيد")
    }

    private fun showMore() {
        val (r, b) = pageRoot("المزيد", "جميع أقسام نظام البقالة المحاسبي")
        listOf("المشتريات", "العملاء", "الموردون", "الحسابات والصناديق", "التقارير", "المطبوعات", "الإعدادات", "المستخدمون والصلاحيات", "النسخ الاحتياطي", "تسجيل العمليات").forEach { x -> b.addView(row(x) { toast("فتح $x") }, LinearLayout.LayoutParams(-1, dp(53)).apply { bottomMargin = dp(6) }) }
        finish(r, "المزيد")
    }

    private fun toast(message: String) = Toast.makeText(this, message, Toast.LENGTH_SHORT).show()
}

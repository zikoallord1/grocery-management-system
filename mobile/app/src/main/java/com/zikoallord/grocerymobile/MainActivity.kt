package com.zikoallord.grocerymobile

import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.text.TextUtils
import android.view.Gravity
import android.view.View
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.WindowCompat

class MainActivity : AppCompatActivity() {
    private val blue = Color.rgb(8, 113, 232)
    private val dark = Color.rgb(3, 55, 104)
    private val headerBlue = Color.rgb(5, 72, 132)
    private val soft = Color.rgb(238, 247, 255)
    private val bg = Color.rgb(246, 250, 253)
    private val white = Color.WHITE
    private val text = Color.rgb(12, 57, 104)
    private val muted = Color.rgb(86, 112, 137)
    private val green = Color.rgb(14, 178, 111)
    private val orange = Color.rgb(246, 139, 9)
    private val purple = Color.rgb(105, 70, 218)
    private val red = Color.rgb(235, 55, 70)

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        WindowCompat.setDecorFitsSystemWindows(window, true)
        window.statusBarColor = dark
        window.navigationBarColor = dark
        showHome()
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun tv(s: String, size: Float, color: Int = text, bold: Boolean = false): TextView =
        TextView(this).apply {
            text = s
            textSize = size
            setTextColor(color)
            gravity = Gravity.CENTER_VERTICAL or Gravity.RIGHT
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            if (bold) setTypeface(typeface, Typeface.BOLD)
        }

    private fun root() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(bg)
        layoutDirection = View.LAYOUT_DIRECTION_RTL
    }

    private fun header(title: String = "نظام البقالة المحاسبي", subtitle: String = "إدارة شاملة .. لمتجرك بكل سهولة"): View {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(headerBlue)
            setPadding(dp(10), dp(7), dp(10), dp(7))
            gravity = Gravity.CENTER_VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        val menu = tv("☰", 22f, white, true).apply { gravity = Gravity.CENTER }
        box.addView(menu, LinearLayout.LayoutParams(dp(38), dp(52)))
        val logo = tv("▣", 25f, white, true).apply { gravity = Gravity.CENTER; setBackgroundColor(blue) }
        box.addView(logo, LinearLayout.LayoutParams(dp(52), dp(52)))
        val names = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(8), 0, 0, 0) }
        names.addView(tv(title, 18f, white, true), LinearLayout.LayoutParams(-1, dp(28)))
        names.addView(tv(subtitle, 10f, Color.rgb(220, 238, 255)), LinearLayout.LayoutParams(-1, dp(20)))
        box.addView(names, LinearLayout.LayoutParams(0, dp(55), 1f))
        box.addView(tv("🔔", 18f, white, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(42), dp(52)))
        return box
    }

    private fun ticker(): View = tv(
        "✓  تم استلام دفعة من المورد 8,320 ريال     ⚠  المخزون منخفض على بعض الأصناف     ✓  تم تسجيل عملية بيع جديدة بقيمة 12,450 ريال",
        10f, white, true
    ).apply {
        setBackgroundColor(blue)
        gravity = Gravity.CENTER
        setPadding(dp(5), dp(4), dp(5), dp(4))
        maxLines = 1
        ellipsize = TextUtils.TruncateAt.MARQUEE
        isSelected = true
        marqueeRepeatLimit = -1
    }

    private fun bottom(active: String): View {
        val bar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(white)
            elevation = dp(8).toFloat()
            setPadding(dp(2), dp(2), dp(2), dp(2))
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        listOf("الرئيسية", "المبيعات", "المخزون", "الكاميرات", "المزيد").forEach { name ->
            val b = tv(if (name == active) "●\n$name" else "○\n$name", 9f, if (name == active) blue else muted, name == active).apply {
                gravity = Gravity.CENTER
                setPadding(0, dp(2), 0, dp(1))
                if (name == active) setBackgroundColor(soft)
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
            bar.addView(b, LinearLayout.LayoutParams(0, dp(60), 1f))
        }
        return bar
    }

    private fun footer(): View {
        val f = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(dark)
            setPadding(dp(7), dp(5), dp(7), dp(5))
            gravity = Gravity.CENTER_VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
        }
        f.addView(tv("نظام البقالة المحاسبي", 11f, white, true), LinearLayout.LayoutParams(0, dp(38), 1.15f))
        f.addView(tv("تصميم وتنفيذ المهندس / زكريا الحاج", 9f, white, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(0, dp(38), 1.45f))
        f.addView(tv("واتساب  772233564", 10f, white, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(0, dp(38), 1f))
        f.addView(tv("Android", 8f, Color.rgb(190, 225, 255)), LinearLayout.LayoutParams(dp(45), dp(38)))
        return f
    }

    private fun pageBody(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(10), dp(8), dp(10), dp(10))
        layoutDirection = View.LAYOUT_DIRECTION_RTL
    }

    private fun finish(r: LinearLayout, active: String) {
        r.addView(footer(), LinearLayout.LayoutParams(-1, dp(48)))
        r.addView(bottom(active), LinearLayout.LayoutParams(-1, dp(64)))
        setContentView(r)
    }

    private fun section(s: String) = tv(s, 16f, text, true).apply { setPadding(0, dp(3), 0, dp(5)) }

    private fun card(title: String, value: String, color: Int, icon: String): View {
        val c = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(white); setPadding(dp(9), dp(7), dp(9), dp(7)); elevation = dp(2).toFloat(); layoutDirection = View.LAYOUT_DIRECTION_RTL }
        val top = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        top.addView(tv(title, 10f, text, true), LinearLayout.LayoutParams(0, dp(24), 1f))
        top.addView(tv(icon, 18f, color, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(28), dp(24)))
        c.addView(top)
        c.addView(tv(value, 20f, color, true), LinearLayout.LayoutParams(-1, dp(31)))
        c.addView(tv("ريال", 9f, muted), LinearLayout.LayoutParams(-1, dp(15)))
        return c
    }

    private fun row(label: String, value: String = "", action: (() -> Unit)? = null): View {
        val r = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; setBackgroundColor(white); setPadding(dp(9), dp(5), dp(9), dp(5)); gravity = Gravity.CENTER_VERTICAL; elevation = dp(1).toFloat(); layoutDirection = View.LAYOUT_DIRECTION_RTL }
        r.addView(tv(label, 11f, text, true), LinearLayout.LayoutParams(0, dp(42), 1f))
        if (value.isNotEmpty()) r.addView(tv(value, 10f, muted).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(105), dp(42)))
        r.addView(tv("›", 21f, blue, true).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(dp(25), dp(42)))
        if (action != null) r.setOnClickListener { action() }
        return r
    }

    private fun button(label: String, action: () -> Unit, fill: Int = white): TextView = tv(label, 11f, if (fill == white) blue else white, true).apply {
        setBackgroundColor(fill); gravity = Gravity.CENTER; setPadding(dp(6), dp(6), dp(6), dp(6)); elevation = dp(1).toFloat(); setOnClickListener { action() }
    }

    private fun pageRoot(title: String, subtitle: String): Pair<LinearLayout, LinearLayout> {
        val r = root(); r.addView(header(title, subtitle)); r.addView(ticker(), LinearLayout.LayoutParams(-1, dp(32)))
        val scroll = ScrollView(this); val b = pageBody(); scroll.addView(b); r.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f)); return Pair(r, b)
    }

    private fun showHome() {
        val r = root(); r.addView(header()); r.addView(ticker(), LinearLayout.LayoutParams(-1, dp(32)))
        val scroll = ScrollView(this); val b = pageBody()
        b.addView(section("لوحة التحكم  |  الفرع الرئيسي"))
        val s1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        s1.addView(card("المبيعات اليوم", "12,450", green, "▥"), LinearLayout.LayoutParams(0, dp(101), 1f))
        s1.addView(card("المشتريات اليوم", "8,320", blue, "🛒"), LinearLayout.LayoutParams(0, dp(101), 1f).apply { marginStart = dp(6) })
        b.addView(s1)
        val s2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL; setPadding(0, dp(6), 0, 0) }
        s2.addView(card("المخزون الحالي", "145", orange, "▣"), LinearLayout.LayoutParams(0, dp(101), 1f))
        s2.addView(card("الأرباح اليوم", "4,130", purple, "↗"), LinearLayout.LayoutParams(0, dp(101), 1f).apply { marginStart = dp(6) })
        b.addView(s2)
        b.addView(section("أحدث العمليات").apply { setPadding(0, dp(10), 0, dp(5)) })
        listOf("مبيعات" to "2,350 ريال", "شراء من المورد" to "4,800 ريال", "إضافة مخزون" to "1,250 ريال", "مصروفات تشغيلية" to "650 ريال").forEach { (a,v) -> b.addView(row(a,v), LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(4) }) }
        b.addView(section("العمليات السريعة").apply { setPadding(0, dp(8), 0, dp(5)) })
        val q1 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        q1.addView(button("＋ مبيعات جديدة", { showSales() }, blue), LinearLayout.LayoutParams(0, dp(46), 1f))
        q1.addView(button("＋ مشتريات", { showMore() }), LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginStart = dp(6) })
        b.addView(q1)
        val q2 = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL; setPadding(0, dp(6), 0, 0) }
        q2.addView(button("＋ إضافة صنف", { showInventory() }), LinearLayout.LayoutParams(0, dp(46), 1f))
        q2.addView(button("▥ تقرير سريع", { showReports() }), LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginStart = dp(6) })
        b.addView(q2)
        scroll.addView(b); r.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f)); finish(r, "الرئيسية")
    }

    private fun showSales() {
        val (r,b) = pageRoot("المبيعات", "فاتورة بيع جديدة وإدارة المبيعات")
        val tabs = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        listOf("بيع جديد","الفواتير","الطلبات").forEach { x -> tabs.addView(button(x,{toast(x)},if(x=="بيع جديد") blue else white),LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(5)}) }
        b.addView(tabs); b.addView(row("🔎  ابحث عن صنف بالاسم أو الباركود..."),LinearLayout.LayoutParams(-1,dp(48)).apply{bottomMargin=dp(6)})
        listOf("مياه معدنية" to "120 متوفر   0.50 ريال","شاي" to "85 متوفر   1.25 ريال","سكر" to "60 متوفر   2.00 ريال","زيت نباتي" to "45 متوفر   3.50 ريال","أرز" to "30 متوفر   7.50 ريال").forEach{(n,v)->b.addView(row(n,v){toast("إضافة $n إلى الفاتورة")},LinearLayout.LayoutParams(-1,dp(53)).apply{bottomMargin=dp(5)})}
        b.addView(tv("إجمالي الفاتورة    0.00 ريال",18f,green,true).apply{setBackgroundColor(Color.rgb(231,250,242));gravity=Gravity.CENTER;setPadding(0,dp(8),0,dp(8))},LinearLayout.LayoutParams(-1,dp(52))); finish(r,"المبيعات")
    }

    private fun showInventory() {
        val (r,b)=pageRoot("المخزون","إدارة الأصناف والكميات والأسعار والباركود")
        b.addView(row("🔎  ابحث عن صنف..."),LinearLayout.LayoutParams(-1,dp(48)).apply{bottomMargin=dp(7)})
        val f=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;layoutDirection=View.LAYOUT_DIRECTION_RTL}
        listOf("جميع الأصناف","الأكثر مبيعًا","الأقل مخزونًا","حسب الكمية").forEach{x->f.addView(button(x,{toast(x)},if(x=="جميع الأصناف")blue else white),LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(4)})}; b.addView(f)
        listOf("مياه معدنية" to "120   شراء 0.35   بيع 0.50","شاي" to "85   شراء 0.90   بيع 1.25","سكر" to "60   شراء 1.50   بيع 2.00","زيت نباتي" to "45   شراء 2.80   بيع 4.00","أرز" to "30   شراء 4.50   بيع 7.50","دقيق" to "50   شراء 0.80   بيع 3.00").forEach{(n,v)->b.addView(row(n,v),LinearLayout.LayoutParams(-1,dp(53)).apply{topMargin=dp(5)})}
        b.addView(tv("إجمالي المخزون    7,190 ريال",14f,green,true).apply{setBackgroundColor(Color.rgb(231,250,242));gravity=Gravity.CENTER;setPadding(0,dp(9),0,dp(9))},LinearLayout.LayoutParams(-1,dp(47)).apply{topMargin=dp(6)}); finish(r,"المخزون")
    }

    private fun showCameras() {
        val (r,b)=pageRoot("مراقبة الكاميرات","متابعة الكاميرات من داخل نظام البقالة")
        val f=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;layoutDirection=View.LAYOUT_DIRECTION_RTL}
        listOf("جميع الكاميرات","متصلة","غير متصلة").forEach{x->f.addView(button(x,{toast(x)},if(x=="جميع الكاميرات")blue else white),LinearLayout.LayoutParams(0,dp(42),1f).apply{marginStart=dp(5)})}; b.addView(f)
        listOf("الكاميرا 1" to "مدخل المحل","الكاميرا 2" to "قسم المواد الغذائية","الكاميرا 3" to "المخزن","الكاميرا 4" to "صالة البيع","الكاميرا 5" to "المحاسبة").forEach{(n,p)->
            val c=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL;setBackgroundColor(white);setPadding(dp(8),dp(6),dp(8),dp(6));gravity=Gravity.CENTER_VERTICAL;layoutDirection=View.LAYOUT_DIRECTION_RTL;elevation=dp(1).toFloat()}
            c.addView(tv("▣",25f,blue,true).apply{gravity=Gravity.CENTER},LinearLayout.LayoutParams(dp(48),dp(48)))
            val info=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL;setPadding(dp(7),0,0,0)}; info.addView(tv(n,12f,text,true),LinearLayout.LayoutParams(-1,dp(24))); info.addView(tv("● متصلة  •  $p",9f,green),LinearLayout.LayoutParams(-1,dp(21))); c.addView(info,LinearLayout.LayoutParams(0,dp(52),1f)); b.addView(c,LinearLayout.LayoutParams(-1,dp(62)).apply{bottomMargin=dp(5)})
        }
        b.addView(button("＋ إضافة كاميرا",{toast("إضافة كاميرا")},blue),LinearLayout.LayoutParams(-1,dp(47)).apply{topMargin=dp(5)}); finish(r,"الكاميرات")
    }

    private fun showReports(){val(r,b)=pageRoot("التقارير","تقارير المبيعات والمخزون والمالية");listOf("تقرير المبيعات اليومية","تقرير الأصناف الأكثر مبيعًا","تقرير المخزون المنخفض","تقرير العملاء","تقرير المشتريات","التقرير المالي").forEach{x->b.addView(row(x){toast("فتح $x")},LinearLayout.LayoutParams(-1,dp(52)).apply{bottomMargin=dp(5)})};finish(r,"المزيد")}

    private fun showMore(){val(r,b)=pageRoot("المزيد","جميع أقسام نظام البقالة المحاسبي");listOf("المشتريات","العملاء","الموردون","الحسابات والصناديق","التقارير","المطبوعات","الإعدادات","المستخدمون والصلاحيات","النسخ الاحتياطي","تسجيل العمليات").forEach{x->b.addView(row(x){toast("فتح $x")},LinearLayout.LayoutParams(-1,dp(52)).apply{bottomMargin=dp(5)})};finish(r,"المزيد")}

    private fun toast(message:String)=Toast.makeText(this,message,Toast.LENGTH_SHORT).show()
}

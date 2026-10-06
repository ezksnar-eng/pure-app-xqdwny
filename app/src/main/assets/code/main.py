package com.example.manhwatranslator

import android.app.Activity
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.IBinder
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import java.io.File
import java.io.FileOutputStream

// =================================================================
// 1. الواجهة الرئيسية للبرنامج (لتغيير الصورة واختيارها من المعرض)
// =================================================================
class MainActivity : AppCompatActivity() {

    private lateinit var imgPreview: ImageView

    private val imagePickerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val imageUri: Uri? = result.data?.data
            imageUri?.let { uri ->
                saveImageToInternalStorage(uri)
                imgPreview.setImageURI(uri)
                Toast.makeText(this, "تم تغيير صورة الشاشة العائمة بنجاح!", Toast.LENGTH_SHORT).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate()

        // بناء الواجهة برمجياً بملف واحد
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(40, 40, 40, 40)
        }

        val title = TextView(this).apply {
            text = "مترجم المانهوا العائم"
            textSize = 22f
            setTextColor(Color.BLACK)
            gravity = Gravity.CENTER
        }

        imgPreview = ImageView(this).apply {
            val savedFile = File(filesDir, "floating_avatar.png")
            if (savedFile.exists()) {
                setImageBitmap(BitmapFactory.decodeFile(savedFile.absolutePath))
            } else {
                setImageResource(android.R.drawable.ic_menu_gallery)
            }
            layoutParams = LinearLayout.LayoutParams(250, 250).apply {
                topMargin = 30
                bottomMargin = 30
            }
        }

        // 🔘 زر اختيار صورة جديدة من المعرض/الاستوديو بداخل التطبيق
        val btnSelectImage = Button(this).apply {
            text = "🖼️ تغيير صورة الأيقونة العائمة"
            setOnClickListener {
                val intent = Intent(Intent.ACTION_PICK).apply {
                    type = "image/*"
                }
                imagePickerLauncher.launch(intent)
            }
        }

        // 🚀 زر تشغيل النافذة العائمة
        val btnStart = Button(this).apply {
            text = "▶️ تشغيل الشاشة العائمة"
            setOnClickListener {
                if (checkOverlayPermission()) {
                    startService(Intent(this@MainActivity, FloatingTranslatorService::class.java))
                } else {
                    requestOverlayPermission()
                }
            }
        }

        layout.addView(title)
        layout.addView(imgPreview)
        layout.addView(btnSelectImage)
        layout.addView(btnStart)

        setContentView(layout)
    }

    private fun saveImageToInternalStorage(uri: Uri) {
        val inputStream = contentResolver.openInputStream(uri)
        val file = File(filesDir, "floating_avatar.png")
        val outputStream = FileOutputStream(file)
        inputStream?.copyTo(outputStream)
        inputStream?.close()
        outputStream.close()
    }

    private fun checkOverlayPermission(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            Settings.canDrawOverlays(this)
        } else true
    }

    private fun requestOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            startActivity(intent)
        }
    }
}

// =================================================================
// 2. خدمة النافذة العائمة (تستخدم الصورة المختارة + زر إغلاق داخلي)
// =================================================================
class FloatingTranslatorService : Service() {

    private lateinit var windowManager: WindowManager
    private lateinit var floatingView: FrameLayout
    private lateinit var params: WindowManager.LayoutParams

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        floatingView = FrameLayout(this)

        // خلفية دائريّة للأيقونة
        val circularBackground = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.parseColor("#44000000"))
            setStroke(3, Color.WHITE)
        }
        floatingView.background = circularBackground

        // جلب الصورة التي اختارها المستخدم من الاستوديو بداخل التطبيق
        val avatarImageView = ImageView(this).apply {
            scaleType = ImageView.ScaleType.CENTER_CROP
            val savedFile = File(filesDir, "floating_avatar.png")
            if (savedFile.exists()) {
                setImageBitmap(BitmapFactory.decodeFile(savedFile.absolutePath))
            } else {
                setImageResource(android.R.drawable.sym_def_app_icon)
            }
        }

        val iconParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.MATCH_PARENT,
            FrameLayout.LayoutParams.MATCH_PARENT
        )
        floatingView.addView(avatarImageView, iconParams)

        // ❌ منطقة الإغلاق بداخل النافذة العائمة نفسها
        val closeBtn = TextView(this).apply {
            text = " ✕ "
            setTextColor(Color.WHITE)
            textSize = 12f
            setBackgroundColor(Color.RED)
            setOnClickListener {
                stopSelf() // إغلاق الشاشة العائمة فوراً
            }
        }
        val closeParams = FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
        }
        floatingView.addView(closeBtn, closeParams)

        // إعدادات العرض العائم
        val layoutFlag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            WindowManager.LayoutParams.TYPE_PHONE
        }

        params = WindowManager.LayoutParams(
            150, 150, // حجم الدائرة العائمة
            layoutFlag,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 100
            y = 200
        }

        // سحب الأيقونة العائمة والضغط للترجمة
        floatingView.setOnTouchListener(object : View.OnTouchListener {
            private var initialX = 0
            private var initialY = 0
            private var initialTouchX = 0f
            private var initialTouchY = 0f
            private var isClick = false

            override fun onTouch(v: View?, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = params.x
                        initialY = params.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        isClick = true
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        val dx = (event.rawX - initialTouchX).toInt()
                        val dy = (event.rawY - initialTouchY).toInt()
                        if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                            isClick = false
                        }
                        params.x = initialX + dx
                        params.y = initialY + dy
                        windowManager.updateViewLayout(floatingView, params)
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        if (isClick) {
                            Toast.makeText(applicationContext, "جاري مسح المانهوا وترجمتها...", Toast.LENGTH_SHORT).show()
                        }
                        return true
                    }
                }
                return false
            }
        })

        windowManager.addView(floatingView, params)
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::floatingView.isInitialized) {
            windowManager.removeView(floatingView)
        }
    }
}

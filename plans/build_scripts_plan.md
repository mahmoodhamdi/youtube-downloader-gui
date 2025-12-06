# خطة إنشاء ملفات Build Scripts لـ YouTube Downloader Pro

## نظرة عامة
إنشاء 3 ملفات batch احترافية للـ build process زي اللي موجودة في Salamah Checker، لكن مخصصة لمشروع YouTube Downloader Pro.

## الملفات المطلوبة

### 1. `bats\build.bat`
**الوظيفة**: بناء التطبيق من الـ source code

**الخطوات**:
1. التحقق من Python
2. تعيين الـ version
3. إنشاء ملف version.py
4. تثبيت الـ dependencies
5. تنظيف الـ builds السابقة
6. بناء التطبيق باستخدام PyInstaller
7. نسخ الملفات الإضافية (LICENSE, README)
8. إنشاء ملف ZIP محمول

**الـ hidden imports المطلوبة**:
- `yt_dlp`
- `PIL` (pillow)
- `tkinter`
- `requests`

### 2. `bats\build_installer.bat`
**الوظيفة**: إنشاء installer باستخدام Inno Setup

**الخطوات**:
1. التحقق من وجود الـ build
2. البحث عن Inno Setup
3. تشغيل ISCC لبناء الـ installer
4. عرض مسار الـ output

**المتطلبات**:
- Inno Setup 6 مثبت على الجهاز
- إنشاء ملف `installer\setup.iss`

### 3. `bats\release.bat`
**الوظيفة**: عملية release كاملة واحترافية

**الخطوات** (12 خطوة):
1. التحقق من نظام Windows
2. التحقق من Python
3. التحقق من الملفات المصدرية
4. تنظيف البيئة
5. إنشاء هيكل البناء
6. إنشاء Virtual Environment
7. تفعيل الـ venv
8. ترقية أدوات البناء
9. تثبيت الـ dependencies
10. (اختياري) تشغيل الاختبارات
11. بناء التطبيق
12. إنشاء حزمة التوزيع

**المميزات**:
- ألوان في الـ console
- logging كامل لملفات
- backup للـ releases السابقة
- SHA256 checksum
- إنشاء launcher scripts

## ملفات إضافية مطلوبة

### `installer\setup.iss`
ملف Inno Setup للـ Windows installer

### `src\version.py`
ملف يتم إنشاؤه تلقائياً يحتوي على:
```python
VERSION = "2.0.0"
BUILD_DATE = "..."
```

## هيكل المجلدات بعد التنفيذ

```
youtube-downloader-gui/
├── bats/
│   ├── build.bat           # بناء بسيط
│   ├── build_installer.bat # بناء installer
│   └── release.bat         # release كامل
├── installer/
│   ├── setup.iss           # Inno Setup script
│   └── Output/             # مكان الـ installer
├── build/                  # ملفات البناء المؤقتة
├── dist/                   # الـ executable
├── release/                # حزمة التوزيع النهائية
├── logs/                   # سجلات البناء
└── backup/                 # نسخ احتياطية
```

## طريقة الاستخدام بعد التنفيذ

### بناء بسيط:
```cmd
cd youtube-downloader-gui
bats\build.bat
# أو مع version محدد:
bats\build.bat 2.1.0
```

### بناء installer:
```cmd
bats\build.bat 2.1.0
bats\build_installer.bat 2.1.0
```

### release كامل:
```cmd
bats\release.bat
```

## الـ Output المتوقع

1. **dist\YouTubeDownloaderPro\** - مجلد التطبيق
2. **dist\YouTubeDownloaderPro-{VERSION}-portable.zip** - نسخة محمولة
3. **installer\Output\YouTubeDownloaderPro-Setup.exe** - الـ installer
4. **release\YouTubeDownloaderPro_v{VERSION}_{TIMESTAMP}.zip** - حزمة كاملة

## ملاحظات هامة

- التطبيق يستخدم `main.py` كـ entry point (مش `gui.py`)
- الـ dependencies الرئيسية: `yt-dlp`, `pillow`, `requests`, `tkinter`
- لا يحتاج Playwright (مختلف عن Salamah Checker)
- يجب التأكد من وجود FFmpeg في PATH للوظائف الكاملة

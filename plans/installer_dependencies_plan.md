# خطة تحسين Installer مع تحميل Dependencies

## نظرة عامة
تعديل الـ installer عشان يعمل check على كل الـ dependencies المطلوبة ويحملها أوتوماتيك لو مش موجودة.

## الـ Dependencies المطلوبة

| Dependency | مطلوب؟ | الوظيفة |
|------------|--------|---------|
| FFmpeg | اختياري (موصى به) | دمج الفيديو والصوت، تحويل الصيغ |
| yt-dlp | مدمج في التطبيق | تحميل الفيديوهات |
| Python | مدمج في التطبيق | تشغيل البرنامج |

## الخطة

### 1. تعديل `installer\setup.iss`
- إضافة صفحة custom للـ dependencies
- Check على FFmpeg بعد التثبيت
- عرض خيار تحميل FFmpeg

### 2. إنشاء `installer\scripts\install_ffmpeg.bat`
سكريبت لتحميل وتثبيت FFmpeg أوتوماتيك:
- تحميل FFmpeg من GitHub releases
- فك الضغط
- إضافته للـ PATH
- التحقق من التثبيت

### 3. إنشاء `installer\scripts\check_dependencies.bat`
سكريبت للتحقق من كل الـ dependencies:
- FFmpeg
- Visual C++ Redistributable (لو مطلوب)

## طريقة العمل

```
[تثبيت التطبيق]
        ↓
[Check FFmpeg موجود؟]
        ↓
    لا ← [عرض رسالة: هل تريد تحميل FFmpeg؟]
        ↓                    ↓
      نعم                   لا
        ↓                    ↓
[تحميل وتثبيت FFmpeg]   [متابعة بدون FFmpeg]
        ↓                    ↓
[إضافة للـ PATH]        [عرض تحذير]
        ↓                    ↓
      [انتهاء التثبيت]
```

## مصادر التحميل

### FFmpeg
- **المصدر**: https://github.com/BtbN/FFmpeg-Builds/releases
- **الملف**: `ffmpeg-master-latest-win64-gpl.zip`
- **الحجم**: ~130 MB

## معالجة الأخطاء

1. **فشل التحميل**: إعادة المحاولة أو عرض رابط التحميل اليدوي
2. **فشل فك الضغط**: عرض رسالة خطأ واضحة
3. **فشل إضافة PATH**: عرض تعليمات يدوية
4. **عدم وجود انترنت**: تخطي التحميل مع تحذير

## الملفات المطلوب إنشاؤها/تعديلها

1. `installer\setup.iss` - تعديل
2. `installer\scripts\install_ffmpeg.ps1` - جديد (PowerShell أفضل للتحميل)
3. `installer\scripts\check_dependencies.bat` - جديد

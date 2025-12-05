# خطة تنفيذ ميزات Phase 3

## نظرة عامة

تنفيذ 3 ميزات أساسية من Phase 3:
1. Format Selection Preview - معاينة الصيغ المتاحة
2. Playlist Filtering - فلترة قوائم التشغيل
3. Auto-Update yt-dlp - التحديث التلقائي لـ yt-dlp

---

## 1. Format Selection Preview (معاينة الصيغ)

### الهدف
السماح للمستخدم بمعاينة جميع الصيغ المتاحة للفيديو واختيار الصيغة المناسبة قبل التحميل.

### الملفات المطلوبة
```
src/
├── core/
│   └── format_selector.py      # جلب وتحليل الصيغ
└── ui/
    └── dialogs/
        └── format_dialog.py    # نافذة اختيار الصيغة
```

### هيكل الكود

#### format_selector.py
```python
class FormatSelector:
    """جلب وتحليل صيغ الفيديو المتاحة."""

    def get_available_formats(url: str) -> List[FormatInfo]
    def filter_formats(formats, video_only=False, audio_only=False) -> List[FormatInfo]
    def get_best_format(formats, quality: str) -> FormatInfo
    def format_size_estimate(format_info) -> str
```

#### FormatInfo DataClass
```python
@dataclass
class FormatInfo:
    format_id: str
    ext: str
    resolution: str
    fps: int
    vcodec: str
    acodec: str
    filesize: int
    quality_label: str
    has_video: bool
    has_audio: bool
```

#### format_dialog.py
```python
class FormatDialog(tk.Toplevel):
    """نافذة اختيار الصيغة."""

    - عرض جدول بجميع الصيغ
    - فلترة حسب (فيديو فقط / صوت فقط / الكل)
    - ترتيب حسب الجودة أو الحجم
    - معاينة الحجم التقديري
    - زر اختيار وزر إلغاء
```

### سير العمل
```
1. المستخدم يدخل URL
2. المستخدم يضغط "معاينة الصيغ" (زر جديد)
3. النظام يجلب معلومات الصيغ من yt-dlp
4. تظهر نافذة FormatDialog بالصيغ المتاحة
5. المستخدم يختار الصيغة المطلوبة
6. يتم إضافة الفيديو للـ Queue بالصيغة المحددة
```

### التكامل مع الكود الحالي
- إضافة زر "Preview Formats" في `downloads_tab.py`
- تعديل `VideoItem` لدعم `custom_format_id`
- تعديل `DownloadManager` لاستخدام الصيغة المخصصة

---

## 2. Playlist Filtering (فلترة قوائم التشغيل)

### الهدف
السماح للمستخدم بفلترة فيديوهات playlist قبل التحميل (اختيار فيديوهات معينة).

### الملفات المطلوبة
```
src/
├── core/
│   └── playlist_filter.py      # جلب وفلترة الـ playlist
└── ui/
    └── dialogs/
        └── playlist_dialog.py  # نافذة اختيار الفيديوهات
```

### هيكل الكود

#### playlist_filter.py
```python
class PlaylistFilter:
    """جلب وفلترة فيديوهات الـ playlist."""

    def get_playlist_info(url: str) -> PlaylistInfo
    def filter_by_duration(videos, min_sec=0, max_sec=None) -> List[VideoInfo]
    def filter_by_date(videos, after=None, before=None) -> List[VideoInfo]
    def filter_by_index(videos, start=1, end=None) -> List[VideoInfo]
```

#### PlaylistInfo DataClass
```python
@dataclass
class PlaylistInfo:
    title: str
    channel: str
    video_count: int
    videos: List[PlaylistVideoInfo]

@dataclass
class PlaylistVideoInfo:
    index: int
    video_id: str
    title: str
    duration: int
    upload_date: str
    thumbnail: str
```

#### playlist_dialog.py
```python
class PlaylistDialog(tk.Toplevel):
    """نافذة اختيار فيديوهات من playlist."""

    - عرض قائمة الفيديوهات مع checkboxes
    - Select All / Deselect All
    - فلترة حسب:
      * المدة (أقل من / أكثر من)
      * تاريخ الرفع
      * رقم الفيديو (من X إلى Y)
    - بحث في العناوين
    - عرض المدة الإجمالية والحجم التقديري
```

### سير العمل
```
1. المستخدم يدخل URL لـ playlist
2. النظام يكتشف أنه playlist
3. تظهر نافذة PlaylistDialog
4. المستخدم يختار الفيديوهات المطلوبة
5. المستخدم يطبق الفلاتر (اختياري)
6. يتم إضافة الفيديوهات المختارة للـ Queue
```

### التكامل مع الكود الحالي
- تعديل `_add_url_to_queue` في `downloads_tab.py` للكشف عن playlist
- إضافة معالجة خاصة لـ playlist URLs

---

## 3. Auto-Update yt-dlp (التحديث التلقائي)

### الهدف
التحقق من وجود تحديثات لـ yt-dlp وتحديثه تلقائياً.

### الملفات المطلوبة
```
src/
├── core/
│   └── update_manager.py       # إدارة التحديثات
└── ui/
    └── dialogs/
        └── update_dialog.py    # نافذة التحديث
```

### هيكل الكود

#### update_manager.py
```python
class UpdateManager:
    """إدارة تحديثات yt-dlp."""

    def get_current_version() -> str
    def check_for_updates() -> Optional[UpdateInfo]
    def update_ytdlp(callback=None) -> bool
    def get_changelog(version: str) -> str
```

#### UpdateInfo DataClass
```python
@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    release_date: str
    changelog: str
    download_url: str
```

#### update_dialog.py
```python
class UpdateDialog(tk.Toplevel):
    """نافذة التحديث."""

    - عرض الإصدار الحالي
    - عرض الإصدار الجديد
    - عرض التغييرات (changelog)
    - زر تحديث الآن
    - خيار "تحقق تلقائياً عند بدء التطبيق"
```

### سير العمل
```
1. عند بدء التطبيق (اختياري) أو يدوياً
2. النظام يتحقق من آخر إصدار من PyPI
3. إذا وُجد تحديث، تظهر نافذة UpdateDialog
4. المستخدم يختار التحديث أو التأجيل
5. إذا اختار التحديث:
   - تشغيل pip install --upgrade yt-dlp
   - عرض نتيجة التحديث
```

### التكامل مع الكود الحالي
- إضافة زر "Check for Updates" في Settings Tab
- إضافة خيار "Auto-check updates" في الإعدادات
- التحقق عند بدء التطبيق (إذا مفعّل)

---

## ترتيب التنفيذ

### المرحلة 1: Auto-Update yt-dlp (الأسهل)
- لا يحتاج تعديلات كبيرة على الـ UI الحالي
- مهم لضمان عمل التطبيق مع YouTube

### المرحلة 2: Format Selection Preview
- يحتاج UI جديد لكن معزول
- يُحسّن تجربة المستخدم بشكل كبير

### المرحلة 3: Playlist Filtering
- الأكثر تعقيداً
- يحتاج تكامل أعمق مع downloads_tab

---

## الملفات الجديدة المطلوبة

```
src/
├── core/
│   ├── format_selector.py    # NEW
│   ├── playlist_filter.py    # NEW
│   └── update_manager.py     # NEW
└── ui/
    └── dialogs/
        ├── __init__.py       # UPDATE
        ├── format_dialog.py  # NEW
        ├── playlist_dialog.py # NEW
        └── update_dialog.py  # NEW
```

---

## الملفات المعدّلة

| الملف | التعديلات |
|-------|-----------|
| `src/ui/tabs/downloads_tab.py` | إضافة زر Preview Formats + معالجة Playlist |
| `src/ui/tabs/settings_tab.py` | إضافة قسم Updates |
| `src/core/download_manager.py` | دعم custom format_id |
| `src/core/queue_manager.py` | إضافة format_id لـ VideoItem |
| `src/config/defaults.py` | إضافة إعدادات التحديث التلقائي |

---

## التحقق بعد التنفيذ

### Auto-Update (COMPLETED)
- [x] يكتشف الإصدار الحالي
- [x] يتحقق من التحديثات
- [x] يُحدّث yt-dlp بنجاح
- [x] يحفظ إعداد التحقق التلقائي

### Format Selection (COMPLETED)
- [x] يجلب الصيغ المتاحة
- [x] يعرض الصيغ في جدول منظم
- [x] يسمح بالفلترة والترتيب
- [x] يُحمّل بالصيغة المختارة

### Playlist Filtering (COMPLETED)
- [x] يكتشف playlist URLs
- [x] يجلب قائمة الفيديوهات
- [x] يسمح بالاختيار والفلترة
- [x] يُضيف الفيديوهات المختارة للـ Queue

---

## الملفات المُنشأة

| الملف | الحالة |
|-------|--------|
| `src/core/update_manager.py` | DONE |
| `src/core/format_selector.py` | DONE |
| `src/core/playlist_filter.py` | DONE |
| `src/ui/dialogs/update_dialog.py` | DONE |
| `src/ui/dialogs/format_dialog.py` | DONE |
| `src/ui/dialogs/playlist_dialog.py` | DONE |

## الملفات المُعدّلة

| الملف | التعديلات | الحالة |
|-------|-----------|--------|
| `src/core/__init__.py` | إضافة exports | DONE |
| `src/ui/dialogs/__init__.py` | إضافة exports | DONE |
| `src/ui/tabs/settings_tab.py` | إضافة قسم Updates | DONE |
| `src/ui/tabs/downloads_tab.py` | إضافة Preview Formats + Playlist detection | DONE |
| `src/ui/widgets/url_input.py` | إضافة get_url method | DONE |
| `src/config/defaults.py` | إضافة DEFAULT_AUTO_CHECK_UPDATES | DONE |
| `src/exceptions/__init__.py` | إضافة ExtractionError, PostProcessingError | DONE |

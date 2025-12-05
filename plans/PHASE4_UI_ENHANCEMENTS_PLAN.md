# Phase 4: UI Enhancements - Implementation Plan

## نظرة عامة

تنفيذ 3 ميزات UI من Phase 4:
1. System Tray - أيقونة النظام
2. Search/Filter Queue - بحث وفلترة الـ Queue
3. Statistics Dashboard - لوحة الإحصائيات

---

## 1. System Tray (COMPLETED)

### الملفات المُنشأة
- `src/ui/system_tray.py`

### الميزات
- أيقونة في منطقة الإشعارات
- قائمة منبثقة مع خيارات:
  - Show/Hide Window
  - Start/Pause/Stop Downloads
  - Quit
- تحديث حالة التحميل في Tooltip
- إشعارات سطح المكتب
- تكامل مع MainWindow

### الاستخدام
```python
from src.ui.system_tray import SystemTray, TrayCallbacks

callbacks = TrayCallbacks(
    on_show=show_window,
    on_quit=quit_app
)
tray = SystemTray(callbacks)
tray.start()
tray.show_notification("Download Complete", "video.mp4")
```

### الملاحظات
- يتطلب `pystray` و `pillow`
- يعمل على Windows, macOS, Linux
- Fallback graceful إذا لم تتوفر المكتبات

---

## 2. Search/Filter Queue (COMPLETED)

### الملفات المُنشأة
- `src/ui/widgets/queue_search.py`

### الميزات
- بحث نصي في العناوين (مع debounce)
- فلترة حسب الحالة:
  - All / Queued / Downloading / Completed / Failed / Paused
- خيارات الترتيب:
  - Date Added / Title A-Z / Title Z-A / Duration / Size
- زر Clear للمسح
- عداد النتائج

### الاستخدام
```python
from src.ui.widgets.queue_search import QueueSearchWidget, QueueFilter

search = QueueSearchWidget(parent)
search.on_filter_changed = lambda search, status, sort: update_queue()

# Apply filters
filtered = QueueFilter.apply(items, search_text="video", status="queued")
```

---

## 3. Statistics Dashboard (COMPLETED)

### الملفات المُنشأة
- `src/ui/tabs/statistics_tab.py`

### الميزات
- بطاقات نظرة عامة:
  - Total Downloads
  - Successful
  - Failed
  - Success Rate
- إحصائيات البيانات:
  - Total Downloaded (size)
  - Total Video Duration
  - Average Speed
  - Last Download Time
- توزيع الجودة (Quality Distribution)
- رسم بياني للتحميلات اليومية (آخر 7 أيام)
- قائمة أكثر القنوات تحميلاً (Top 5)
- حفظ الإحصائيات في ملف JSON
- زر Reset Stats

### الاستخدام
```python
from src.ui.tabs.statistics_tab import StatisticsTab, StatisticsManager

stats_manager = StatisticsManager()
tab = StatisticsTab(notebook, stats_manager)

# Record a download
stats_manager.record_download(
    success=True,
    bytes_downloaded=150_000_000,
    duration_seconds=600,
    speed_bps=5_000_000,
    quality="1080p",
    channel="YouTube Channel"
)
```

---

## الملفات المُنشأة

| الملف | الحالة |
|-------|--------|
| `src/ui/system_tray.py` | DONE |
| `src/ui/widgets/queue_search.py` | DONE |
| `src/ui/tabs/statistics_tab.py` | DONE |

## الملفات المُعدّلة

| الملف | التعديلات | الحالة |
|-------|-----------|--------|
| `src/ui/__init__.py` | إضافة SystemTray exports | DONE |
| `src/ui/widgets/__init__.py` | إضافة QueueSearchWidget | DONE |
| `src/ui/tabs/__init__.py` | إضافة StatisticsTab | DONE |

---

## التكامل مع MainWindow

### System Tray
```python
# في main_window.py
from src.ui.system_tray import SystemTrayManager

self.tray_manager = SystemTrayManager(self, self.config)
self.tray_manager.setup()

# عند minimize
def on_minimize():
    if self.config.get("minimize_to_tray"):
        self.root.withdraw()
```

### Queue Search
```python
# في downloads_tab.py
from src.ui.widgets.queue_search import QueueSearchWidget

self.search_widget = QueueSearchWidget(self)
self.search_widget.on_filter_changed = self._apply_queue_filter
```

### Statistics Tab
```python
# في main_window.py
from src.ui.tabs import StatisticsTab, StatisticsManager

self.stats_manager = StatisticsManager()
self.stats_tab = StatisticsTab(self.notebook, self.stats_manager)
self.notebook.add(self.stats_tab, text="Statistics")
```

---

## التحقق

### System Tray
- [x] يظهر في منطقة الإشعارات
- [x] القائمة المنبثقة تعمل
- [x] Show/Hide يعمل
- [x] الإشعارات تظهر

### Queue Search
- [x] البحث يعمل مع debounce
- [x] الفلترة حسب الحالة تعمل
- [x] الترتيب يعمل
- [x] Clear يمسح الفلاتر

### Statistics Dashboard
- [x] البطاقات تعرض الأرقام
- [x] توزيع الجودة يعمل
- [x] الرسم البياني اليومي يعمل
- [x] قائمة القنوات تعمل
- [x] الحفظ والتحميل يعمل
- [x] Reset يعمل

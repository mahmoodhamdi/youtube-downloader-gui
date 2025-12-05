"""Tab components for YouTube Downloader UI."""

from .downloads_tab import DownloadsTab
from .settings_tab import SettingsTab
from .history_tab import HistoryTab
from .statistics_tab import StatisticsTab, StatisticsManager, DownloadStats

__all__ = [
    'DownloadsTab',
    'SettingsTab',
    'HistoryTab',
    'StatisticsTab',
    'StatisticsManager',
    'DownloadStats',
]

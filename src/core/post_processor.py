"""Post-processing for downloaded videos.

This module provides post-processing options using FFmpeg:
- Format conversion
- Audio extraction
- Subtitle embedding
- Thumbnail embedding
- Metadata addition
"""

import os
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class AudioFormat(Enum):
    """Supported audio extraction formats."""
    MP3 = "mp3"
    M4A = "m4a"
    AAC = "aac"
    FLAC = "flac"
    WAV = "wav"
    OPUS = "opus"
    VORBIS = "vorbis"


class VideoFormat(Enum):
    """Supported video conversion formats."""
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"
    FLV = "flv"


class AudioQuality(Enum):
    """Audio quality presets (kbps)."""
    LOW = "96"
    MEDIUM = "128"
    HIGH = "192"
    VERY_HIGH = "256"
    LOSSLESS = "320"
    BEST = "0"  # Best available


@dataclass
class PostProcessingOptions:
    """Post-processing configuration options.

    Attributes:
        embed_subtitles: Embed subtitles into video file
        embed_thumbnail: Embed thumbnail as cover art
        add_metadata: Add metadata (title, description, etc.)
        convert_to: Target video format for conversion
        extract_audio: Extract audio only
        audio_format: Audio format for extraction
        audio_quality: Audio quality for extraction
        keep_original: Keep original file after conversion
        merge_output_format: Format for merged audio+video
        remux_video: Remux video to different container
        normalize_audio: Normalize audio levels
        sponsorblock_remove: Remove sponsor segments
        sponsorblock_mark: Mark sponsor segments as chapters
    """
    embed_subtitles: bool = False
    embed_thumbnail: bool = False
    add_metadata: bool = True
    convert_to: Optional[str] = None
    extract_audio: bool = False
    audio_format: str = "mp3"
    audio_quality: str = "192"
    keep_original: bool = False
    merge_output_format: str = "mp4"
    remux_video: Optional[str] = None
    normalize_audio: bool = False
    sponsorblock_remove: List[str] = field(default_factory=list)
    sponsorblock_mark: List[str] = field(default_factory=list)


class PostProcessor:
    """Handle post-processing of downloaded files.

    Features:
    - Convert video formats (MP4, MKV, WebM, etc.)
    - Extract audio (MP3, M4A, FLAC, etc.)
    - Embed subtitles into video
    - Embed thumbnail as cover art
    - Add metadata to files
    - SponsorBlock integration

    Usage:
        processor = PostProcessor()

        # Check if FFmpeg is available
        if processor.is_ffmpeg_available():
            # Get yt-dlp post-processors
            options = PostProcessingOptions(
                embed_subtitles=True,
                embed_thumbnail=True,
                extract_audio=True,
                audio_format="mp3",
                audio_quality="320"
            )
            postprocessors = processor.get_ydl_postprocessors(options)
    """

    def __init__(self, ffmpeg_path: Optional[str] = None):
        """Initialize post-processor.

        Args:
            ffmpeg_path: Custom path to FFmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()

    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg in system PATH.

        Returns:
            Path to FFmpeg or None
        """
        return shutil.which('ffmpeg')

    def _find_ffprobe(self) -> Optional[str]:
        """Find FFprobe in system PATH.

        Returns:
            Path to FFprobe or None
        """
        return shutil.which('ffprobe')

    def is_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available.

        Returns:
            True if FFmpeg is found
        """
        return self.ffmpeg_path is not None

    def get_ffmpeg_version(self) -> Optional[str]:
        """Get FFmpeg version string.

        Returns:
            Version string or None
        """
        if not self.ffmpeg_path:
            return None

        try:
            import subprocess
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse first line for version
                first_line = result.stdout.split('\n')[0]
                return first_line
            return None
        except Exception:
            return None

    def get_ydl_postprocessors(self, options: PostProcessingOptions) -> List[Dict[str, Any]]:
        """Get yt-dlp postprocessor configuration.

        Args:
            options: Post-processing options

        Returns:
            List of postprocessor dictionaries for yt-dlp
        """
        postprocessors = []

        # Embed subtitles
        if options.embed_subtitles:
            postprocessors.append({
                'key': 'FFmpegEmbedSubtitle',
                'already_have_subtitle': False,
            })

        # Embed thumbnail
        if options.embed_thumbnail:
            postprocessors.append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            })

        # Add metadata
        if options.add_metadata:
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            })

        # Extract audio
        if options.extract_audio:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.audio_format,
                'preferredquality': options.audio_quality,
                'nopostoverwrites': False,
            })

        # Convert video format
        if options.convert_to and not options.extract_audio:
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': options.convert_to,
            })

        # Remux video
        if options.remux_video and not options.extract_audio and not options.convert_to:
            postprocessors.append({
                'key': 'FFmpegVideoRemuxer',
                'preferedformat': options.remux_video,
            })

        # SponsorBlock - remove segments
        if options.sponsorblock_remove:
            postprocessors.append({
                'key': 'SponsorBlock',
                'categories': options.sponsorblock_remove,
                'when': 'after_filter',
            })
            postprocessors.append({
                'key': 'ModifyChapters',
                'remove_sponsor_segments': options.sponsorblock_remove,
                'force_keyframes': False,
            })

        # SponsorBlock - mark as chapters
        if options.sponsorblock_mark and not options.sponsorblock_remove:
            postprocessors.append({
                'key': 'SponsorBlock',
                'categories': options.sponsorblock_mark,
                'when': 'after_filter',
            })
            postprocessors.append({
                'key': 'ModifyChapters',
                'sponsorblock_chapter_title': '[SponsorBlock]: %(category_names)l',
                'force_keyframes': False,
            })

        return postprocessors

    def get_ydl_opts(self, options: PostProcessingOptions) -> Dict[str, Any]:
        """Get complete yt-dlp options for post-processing.

        Args:
            options: Post-processing options

        Returns:
            Dictionary of yt-dlp options
        """
        opts = {
            'postprocessors': self.get_ydl_postprocessors(options),
        }

        # Set FFmpeg location if custom
        if self.ffmpeg_path:
            opts['ffmpeg_location'] = os.path.dirname(self.ffmpeg_path)

        # Keep video when extracting audio
        if options.extract_audio and options.keep_original:
            opts['keepvideo'] = True

        # Write thumbnail for embedding
        if options.embed_thumbnail:
            opts['writethumbnail'] = True

        # Write subtitles for embedding
        if options.embed_subtitles:
            opts['writesubtitles'] = True
            opts['writeautomaticsub'] = True

        # Merge format preference
        if options.merge_output_format:
            opts['merge_output_format'] = options.merge_output_format

        return opts

    @staticmethod
    def get_audio_formats() -> List[str]:
        """Get list of supported audio formats.

        Returns:
            List of format names
        """
        return [f.value for f in AudioFormat]

    @staticmethod
    def get_video_formats() -> List[str]:
        """Get list of supported video formats.

        Returns:
            List of format names
        """
        return [f.value for f in VideoFormat]

    @staticmethod
    def get_audio_qualities() -> List[tuple]:
        """Get list of audio quality options.

        Returns:
            List of (label, value) tuples
        """
        return [
            ("Low (96 kbps)", "96"),
            ("Medium (128 kbps)", "128"),
            ("High (192 kbps)", "192"),
            ("Very High (256 kbps)", "256"),
            ("Maximum (320 kbps)", "320"),
            ("Best Available", "0"),
        ]

    @staticmethod
    def get_sponsorblock_categories() -> List[tuple]:
        """Get SponsorBlock category options.

        Returns:
            List of (label, value) tuples
        """
        return [
            ("Sponsor", "sponsor"),
            ("Intro", "intro"),
            ("Outro", "outro"),
            ("Self Promotion", "selfpromo"),
            ("Preview", "preview"),
            ("Filler", "filler"),
            ("Interaction Reminder", "interaction"),
            ("Music (Non-Music)", "music_offtopic"),
        ]


class FFmpegHelper:
    """Helper utilities for FFmpeg operations."""

    @staticmethod
    def get_media_info(file_path: str) -> Optional[Dict[str, Any]]:
        """Get media file information using FFprobe.

        Args:
            file_path: Path to media file

        Returns:
            Dictionary with media info or None
        """
        ffprobe = shutil.which('ffprobe')
        if not ffprobe:
            return None

        try:
            import subprocess
            import json

            result = subprocess.run([
                ffprobe,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                file_path
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        except Exception:
            return None

    @staticmethod
    def get_duration(file_path: str) -> Optional[float]:
        """Get media file duration in seconds.

        Args:
            file_path: Path to media file

        Returns:
            Duration in seconds or None
        """
        info = FFmpegHelper.get_media_info(file_path)
        if info and 'format' in info:
            try:
                return float(info['format'].get('duration', 0))
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def get_video_resolution(file_path: str) -> Optional[tuple]:
        """Get video resolution.

        Args:
            file_path: Path to video file

        Returns:
            Tuple of (width, height) or None
        """
        info = FFmpegHelper.get_media_info(file_path)
        if info and 'streams' in info:
            for stream in info['streams']:
                if stream.get('codec_type') == 'video':
                    width = stream.get('width')
                    height = stream.get('height')
                    if width and height:
                        return (width, height)
        return None

#!/usr/bin/env python3
"""
Setup script for YouTube Downloader GUI
"""

from setuptools import setup, find_packages
import os

def read_readme():
    """
    Read the README file content.

    Returns:
        str: Content of README.md or a default description if not found.
    """
    try:
        with open("README.md", "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return "YouTube Downloader GUI - A comprehensive tool for downloading YouTube videos and playlists"

def read_requirements():
    """
    Read the requirements file content.

    Returns:
        list: List of dependencies or default dependencies if not found.
    """
    try:
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return ["yt-dlp>=2024.8.6", "pyinstaller>=6.0.0"]

setup(
    name="youtube-downloader-gui",
    version="1.0.0",
    author="Mahmood Hamdi",
    author_email="hmdy7486@gmail.com",
    description="A comprehensive GUI application for downloading YouTube videos and playlists",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/mahmoodhamdi/youtube-downloader-gui",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "youtube-downloader=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.txt", "*.md", "*.ico", "*.png"],
    },
)
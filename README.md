# ReelDrop

> **Educational & Testing Disclaimer:** This repository was created strictly for **personal learning, UI prototyping, and technical testing** — **not** with any malicious intent or to harm content creators or platforms. Please read the full [DISCLAIMER.md](DISCLAIMER.md) before using this code.

<p align="center">
  <img src="assets/mascota.png" width="128" alt="ReelDrop Mascot" />
</p>

**ReelDrop** is a minimalist, cross-platform desktop application (**Windows** & **Linux**) built with **Python**, **CustomTkinter**, **yt-dlp**, and **FFmpeg** (`imageio-ffmpeg`) to test single-input media link detection, stream merging, and universal `H.264 + AAC` MP4 compatibility.

---

## Features

- **Minimalist Single-Input Interface**: Inspired by the clean, distraction-free aesthetic of [cobalt](https://cobalt.tools), featuring custom monochrome line-art mascot artwork.
- **Automatic Platform Detection**: Recognizes links from YouTube, YouTube Shorts, TikTok, Instagram Reels, Facebook, X/Twitter, Reddit, Twitch, SoundCloud, and more as soon as a URL is pasted.
- **Three Processing Modes**:
  - **`auto`** — Video + Audio in universally compatible `.mp4` (`H.264 / avc1` + `AAC-LC`).
  - **`audio`** — Extracts audio track as `.mp3`.
  - **`mute`** — Downloads video stream without audio (`.mp4`).
- **Bundled FFmpeg Support**: Uses `imageio-ffmpeg` automatically when system `ffmpeg` is not installed, re-encoding `VP9` / `AV1` / `HEVC` streams to `H.264` when needed so files play natively on Windows Media Player and Linux media players.
- **Cross-Platform (**Windows & Linux**)**: Native file and folder reveal (`SHOpenFolderAndSelectItems` on Windows, `xdg-open` / `gio` on Linux) and automatic creation of `~/Downloads/ReelDrop` on startup.

---

## Getting Started

### Windows
Double-click **`ejecutar_windows.bat`**, or run from a terminal:
```powershell
py -m pip install -r requirements.txt
py app.py
```

### Linux (Ubuntu / Debian / Fedora / Arch)
Ensure `python3-tk` and `python3-venv` are installed (e.g. `sudo apt install python3-tk python3-venv`), then run:
```bash
chmod +x ejecutar_linux.sh
./ejecutar_linux.sh
```

---

## Legal Notice

This software is provided **"as is"** for educational and testing purposes only. Users are solely responsible for complying with applicable copyright laws and the Terms of Service of any website or platform accessed. See [DISCLAIMER.md](DISCLAIMER.md) for details.

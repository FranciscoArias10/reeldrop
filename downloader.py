"""
Motor multiplataforma (Windows / Linux / macOS) para descarga de videos,
enfocado en Reels (Instagram, Facebook), Shorts (YouTube), TikTok y +1000 plataformas.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

import yt_dlp


class DownloadCancelledError(Exception):
    """Excepción lanzada cuando el usuario cancela la descarga en curso."""


@dataclass
class PlatformInfo:
    key: str
    name: str
    badge: str
    color: str
    is_short_form: bool = False


@dataclass
class VideoMetadata:
    url: str
    title: str
    uploader: str
    duration_seconds: Optional[float]
    duration_str: str
    thumbnail_url: Optional[str]
    platform: PlatformInfo
    view_count: Optional[int] = None
    webpage_url: Optional[str] = None


QUALITY_PRESETS: dict[str, dict[str, str]] = {
    "reel_mp4": {
        "label": "auto (mp4 h.264)",
        "description": "Video + Audio en MP4 H.264 universal",
    },
    "best_mp4": {
        "label": "máxima (1080p / 4k)",
        "description": "Máxima resolución disponible en MP4 H.264",
    },
    "hd_720p": {
        "label": "720p hd",
        "description": "Hasta 720p en MP4 para menor tamaño",
    },
    "sd_480p": {
        "label": "480p compacto",
        "description": "Resolución ligera en MP4",
    },
    "audio_mp3": {
        "label": "audio (mp3)",
        "description": "Extrae únicamente el audio en MP3",
    },
    "mute_mp4": {
        "label": "mute (sin audio)",
        "description": "Descarga el video en MP4 sin pista de audio",
    },
}

BROWSER_COOKIE_OPTIONS: dict[str, Optional[str]] = {
    "sin cookies (público)": None,
    "chrome": "chrome",
    "edge": "edge",
    "firefox": "firefox",
    "brave": "brave",
    "chromium": "chromium",
    "opera": "opera",
}


def detect_platform(url: str) -> PlatformInfo:
    """Detecta automáticamente de qué red social o plataforma proviene el enlace."""
    clean = (url or "").strip()
    if not clean:
        return PlatformInfo("none", "ninguna", "youtube • tiktok • instagram • x • +1000", "#52525B", False)

    lower = clean.lower()
    try:
        parsed = urlparse(clean if "://" in clean else f"https://{clean}")
        host = parsed.netloc.lower()
        path = parsed.path.lower()
    except Exception:
        host = lower
        path = lower

    if any(d in host for d in ("tiktok.com", "vm.tiktok.com", "vt.tiktok.com")):
        return PlatformInfo("tiktok", "TikTok", "♪ tiktok", "#FE2C55", True)

    if any(d in host for d in ("instagram.com", "instagr.am")):
        if "/reel/" in path or "/reels/" in path:
            return PlatformInfo("ig_reel", "Instagram Reels", "◎ instagram reel", "#E1306C", True)
        if "/stories/" in path:
            return PlatformInfo("ig_story", "Instagram Stories", "◎ instagram story", "#C13584", True)
        return PlatformInfo("instagram", "Instagram", "◎ instagram", "#E1306C", True)

    if "music.youtube.com" in host:
        return PlatformInfo("yt_music", "YouTube Music", "♫ youtube music", "#FF0033", False)

    if any(d in host for d in ("youtube.com", "youtu.be", "youtube-nocookie.com")):
        if "/shorts/" in path:
            return PlatformInfo("yt_shorts", "YouTube Shorts", "⚡ youtube shorts", "#FF0033", True)
        return PlatformInfo("youtube", "YouTube", "▶ youtube", "#FF0033", False)

    if any(d in host for d in ("facebook.com", "fb.watch", "fb.com")):
        if "/reel/" in path or "/share/r/" in path:
            return PlatformInfo("fb_reel", "Facebook Reels", "f facebook reel", "#1877F2", True)
        return PlatformInfo("facebook", "Facebook", "f facebook", "#1877F2", False)

    if any(d in host for d in ("x.com", "twitter.com", "t.co")):
        return PlatformInfo("twitter", "X / Twitter", "𝕏 x / twitter", "#1D9BF0", False)

    if any(d in host for d in ("reddit.com", "redd.it", "v.redd.it")):
        return PlatformInfo("reddit", "Reddit", "● reddit", "#FF4500", False)

    if any(d in host for d in ("twitch.tv", "clips.twitch.tv")):
        return PlatformInfo("twitch", "Twitch", "◈ twitch", "#9146FF", True)

    if "soundcloud.com" in host or "on.soundcloud.com" in host:
        return PlatformInfo("soundcloud", "SoundCloud", "☁ soundcloud", "#FF5500", False)

    if any(d in host for d in ("pinterest.com", "pin.it")):
        return PlatformInfo("pinterest", "Pinterest", "● pinterest", "#E60023", True)

    if "threads.net" in host or "threads.com" in host:
        return PlatformInfo("threads", "Threads", "@ threads", "#A1A1AA", True)

    if "bsky.app" in host:
        return PlatformInfo("bluesky", "Bluesky", "🦋 bluesky", "#0285FF", False)

    if "vimeo.com" in host:
        return PlatformInfo("vimeo", "Vimeo", "▶ vimeo", "#1AB7EA", False)

    if "kick.com" in host:
        return PlatformInfo("kick", "Kick", "■ kick", "#53FC18", True)

    if "bilibili.com" in host or "b23.tv" in host:
        return PlatformInfo("bilibili", "Bilibili", "▶ bilibili", "#00A1D6", False)

    if "dailymotion.com" in host or "dai.ly" in host:
        return PlatformInfo("dailymotion", "Dailymotion", "▶ dailymotion", "#0066DC", False)

    if "snapchat.com" in host:
        return PlatformInfo("snapchat", "Snapchat", "● snapchat", "#EAB308", True)

    if "linkedin.com" in host:
        return PlatformInfo("linkedin", "LinkedIn", "in linkedin", "#0A66C2", False)

    if clean.startswith(("http://", "https://")):
        domain = host.replace("www.", "").split(":")[0] or "enlace web"
        return PlatformInfo("generic", domain, f"🌐 {domain}", "#10B981", False)

    return PlatformInfo("unknown", "enlace inválido", "⚠ enlace no reconocido", "#F59E0B", False)


def is_likely_video_url(text: str) -> bool:
    """Verifica si un texto del portapapeles parece un enlace válido de video/red social."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) > 2048 or "\n" in clean or " " in clean:
        return False
    if not re.match(r"^https?://", clean, re.IGNORECASE):
        return False
    info = detect_platform(clean)
    return info.key not in ("none", "unknown")


def get_ffmpeg_path() -> Optional[str]:
    """
    Obtiene la ruta de FFmpeg compatible con Windows y Linux.
    1. Busca en el PATH del sistema (ej. /usr/bin/ffmpeg en Linux o winget/choco en Windows).
    2. Si no está instalado en el sistema, usa el binario precompilado de imageio-ffmpeg.
    """
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass

    return None


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None or seconds < 0:
        return "--:--"
    total = int(round(seconds))
    hrs, rem = divmod(total, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def format_bytes(num_bytes: Optional[float]) -> str:
    if not num_bytes or num_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    val = float(num_bytes)
    for unit in units:
        if val < 1024.0 or unit == units[-1]:
            return f"{val:.1f} {unit}" if unit != "B" else f"{int(val)} B"
        val /= 1024.0
    return f"{val:.1f} GB"


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text or "")


def get_default_download_dir() -> Path:
    """Devuelve la carpeta de descargas por defecto en Windows y Linux."""
    home = Path.home()
    # Comprobar carpetas comunes en Windows y Linux (XDG / Español / Inglés)
    candidates = [
        home / "Downloads",
        home / "Descargas",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            target = candidate / "ReelDrop"
            target.mkdir(parents=True, exist_ok=True)
            return target

    fallback = home / "ReelDrop_Videos"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _reveal_file_on_windows(resolved_file: Path) -> None:
    """
    Abre el Explorador de Windows en la carpeta contenedora seleccionando el archivo.
    Usa la API nativa Win32 (SHOpenFolderAndSelectItems) para evitar el fallo clásico de
    explorer.exe cuando la ruta contiene espacios, comas o corchetes (que abría 'Documentos').
    """
    import ctypes

    try:
        ole32 = ctypes.windll.ole32
        shell32 = ctypes.windll.shell32

        ole32.CoInitialize.argtypes = [ctypes.c_void_p]
        ole32.CoInitialize.restype = ctypes.c_long

        shell32.ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
        shell32.ILCreateFromPathW.restype = ctypes.c_void_p

        shell32.SHOpenFolderAndSelectItems.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_ulong,
        ]
        shell32.SHOpenFolderAndSelectItems.restype = ctypes.c_long

        shell32.ILFree.argtypes = [ctypes.c_void_p]
        shell32.ILFree.restype = None

        ole32.CoInitialize(None)
        pidl = shell32.ILCreateFromPathW(str(resolved_file))
        if pidl:
            try:
                hr = shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
                if hr == 0:
                    return
            finally:
                shell32.ILFree(pidl)
    except Exception:
        pass

    # Respaldo seguro: abrir directamente la carpeta de descargas
    os.startfile(str(resolved_file.parent))  # type: ignore[attr-defined]


def open_path_cross_platform(target_path: Path, reveal_in_folder: bool = False) -> bool:
    """
    Abre un archivo o carpeta de forma nativa en Windows, Linux y macOS.
    Si reveal_in_folder=True y target_path es un archivo, abre el explorador mostrando el archivo.
    """
    try:
        resolved = target_path.resolve()
        if not resolved.exists():
            return False

        if sys.platform.startswith("win"):
            if reveal_in_folder and resolved.is_file():
                _reveal_file_on_windows(resolved)
            else:
                os.startfile(str(resolved))  # type: ignore[attr-defined]
            return True

        if sys.platform == "darwin":
            if reveal_in_folder and resolved.is_file():
                subprocess.Popen(["open", "-R", str(resolved)])
            else:
                subprocess.Popen(["open", str(resolved)])
            return True

        # Linux / BSD (X11 / Wayland)
        folder_or_file = resolved.parent if (reveal_in_folder and resolved.is_file()) else resolved
        if shutil.which("xdg-open"):
            subprocess.Popen(
                ["xdg-open", str(folder_or_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        if shutil.which("gio"):
            subprocess.Popen(
                ["gio", "open", str(folder_or_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
    except Exception:
        return False
    return False


def _build_base_ydl_opts(browser_cookies: Optional[str] = None) -> dict[str, Any]:
    ffmpeg_path = get_ffmpeg_path()
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "windowsfilenames": True,
        "overwrites": True,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 4,
        "nocheckcertificate": False,
        "geo_bypass": True,
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
        },
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path
    if browser_cookies:
        opts["cookiesfrombrowser"] = (browser_cookies,)
    return opts


def fetch_video_info(url: str, browser_cookies: Optional[str] = None) -> VideoMetadata:
    """Obtiene los metadatos y miniatura de cualquier Reel, Short, TikTok o video."""
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("El enlace está vacío.")

    opts = _build_base_ydl_opts(browser_cookies)
    opts["extract_flat"] = False

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(clean_url, download=False)
        if not info:
            raise RuntimeError("No se pudo obtener información del enlace.")

        # Si es una lista o carrusel (ej. post de Instagram o TikTok con varios clips), tomar el primero
        if "entries" in info and info["entries"]:
            entries = [e for e in info["entries"] if e]
            if entries:
                info = entries[0]

        title = (
            info.get("title")
            or info.get("description", "")[:70]
            or f"Video_{info.get('id', 'descarga')}"
        ).strip()
        uploader = (
            info.get("uploader")
            or info.get("channel")
            or info.get("creator")
            or info.get("uploader_id")
            or "Creador desconocido"
        )
        duration = info.get("duration")
        thumbnail = info.get("thumbnail")
        if not thumbnail and info.get("thumbnails"):
            thumbs = [t.get("url") for t in info["thumbnails"] if t.get("url")]
            if thumbs:
                thumbnail = thumbs[-1]

        platform = detect_platform(info.get("webpage_url") or clean_url)
        return VideoMetadata(
            url=clean_url,
            title=title,
            uploader=str(uploader),
            duration_seconds=float(duration) if duration is not None else None,
            duration_str=format_duration(duration),
            thumbnail_url=thumbnail,
            platform=platform,
            view_count=info.get("view_count"),
            webpage_url=info.get("webpage_url") or clean_url,
        )


def _subprocess_no_window_kwargs() -> dict[str, Any]:
    """Evita que se abran ventanas emergentes de consola en Windows al ejecutar FFmpeg."""
    if sys.platform.startswith("win"):
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


def ensure_universal_mp4_compatibility(
    filepath: Path,
    ffmpeg_path: Optional[str],
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    strip_audio: bool = False,
) -> Path:
    """
    Verifica los códecs del archivo descargado.
    Si el video no es H.264 (avc1) o el audio no es AAC-LC estándar (o si strip_audio=True en modo mute),
    lo convierte a MP4 H.264 universal manteniendo la resolución original.
    """
    if not ffmpeg_path or not filepath.exists():
        return filepath

    try:
        probe = subprocess.run(
            [ffmpeg_path, "-hide_banner", "-i", str(filepath)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_subprocess_no_window_kwargs(),
        )
        info_text = probe.stderr or ""
    except Exception:
        return filepath

    video_match = re.search(r"Stream #\d+:\d+.*?: Video:\s*([a-zA-Z0-9_]+)", info_text)
    audio_match = re.search(r"Stream #\d+:\d+.*?: Audio:\s*([a-zA-Z0-9_]+)(?:\s*\(([^)]+)\))?", info_text)

    vcodec = (video_match.group(1).lower() if video_match else "")
    acodec = (audio_match.group(1).lower() if audio_match else "")
    aprofile = ((audio_match.group(2) or "").lower() if audio_match else "")

    needs_video_encode = vcodec != "h264"
    if strip_audio:
        needs_audio_change = bool(audio_match)
    else:
        needs_audio_change = bool(audio_match) and (acodec != "aac" or "he-aac" in aprofile)

    if not needs_video_encode and not needs_audio_change and filepath.suffix.lower() == ".mp4":
        return filepath

    if cancel_event and cancel_event.is_set():
        raise DownloadCancelledError("Descarga cancelada por el usuario.")

    if progress_callback:
        progress_callback(
            {
                "stage": "processing",
                "percent": 0.99,
                "downloaded_str": format_bytes(filepath.stat().st_size),
                "total_str": format_bytes(filepath.stat().st_size),
                "speed_str": "h.264",
                "eta_str": "00:02",
                "message": "optimizando video a mp4 compatible...",
            }
        )

    target_mp4 = filepath.with_suffix(".mp4")
    temp_out = filepath.with_name(f"{filepath.stem}.__h264_tmp__.mp4")

    cmd = [ffmpeg_path, "-y", "-hide_banner", "-i", str(filepath)]
    if needs_video_encode:
        cmd += [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
        ]
    else:
        cmd += ["-c:v", "copy"]

    if strip_audio:
        cmd += ["-an"]
    elif audio_match:
        if needs_audio_change:
            cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "44100"]
        else:
            cmd += ["-c:a", "copy"]

    cmd += ["-movflags", "+faststart", str(temp_out)]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            **_subprocess_no_window_kwargs(),
        )
        if proc.returncode == 0 and temp_out.exists() and temp_out.stat().st_size > 0:
            if filepath != target_mp4 and filepath.exists():
                try:
                    filepath.unlink()
                except Exception:
                    pass
            os.replace(temp_out, target_mp4)
            return target_mp4
    except Exception:
        pass
    finally:
        if temp_out.exists():
            try:
                temp_out.unlink()
            except Exception:
                pass

    return filepath


def download_video(
    url: str,
    output_dir: Path,
    quality_key: str = "reel_mp4",
    browser_cookies: Optional[str] = None,
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> tuple[Path, VideoMetadata]:
    """
    Descarga un video/Reel/Short/TikTok en la carpeta indicada.
    Devuelve (ruta_del_archivo_final, VideoMetadata).
    """
    clean_url = url.strip()
    if not clean_url:
        raise ValueError("Por favor ingresa un enlace válido.")

    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = get_ffmpeg_path()
    has_ffmpeg = ffmpeg_path is not None

    opts = _build_base_ydl_opts(browser_cookies)
    opts["outtmpl"] = {
        "default": str(output_dir / "%(title).95B [%(id)s].%(ext)s"),
    }

    # Selección de formato optimizada según calidad y disponibilidad de FFmpeg
    if quality_key == "audio_mp3":
        opts["format"] = "bestaudio/best"
        if has_ffmpeg:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
    elif quality_key == "mute_mp4":
        if has_ffmpeg:
            opts["format"] = "bestvideo/best"
            opts["format_sort"] = ["vcodec:h264", "ext:mp4"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "bestvideo[ext=mp4]/best[ext=mp4]/best"
    elif quality_key == "reel_mp4":
        # Prioriza H.264 (avc1) + AAC nativo cuando existe en la misma resolución;
        # si la red social (ej. Instagram Reels 1080p) solo entrega VP9/HEVC/AV1,
        # se convierte automáticamente a H.264 + AAC al finalizar.
        if has_ffmpeg:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["format_sort"] = ["vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "best[ext=mp4]/best"
    elif quality_key == "best_mp4":
        if has_ffmpeg:
            opts["format"] = "bestvideo+bestaudio/best"
            opts["format_sort"] = ["res", "vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "best[ext=mp4]/best"
    elif quality_key == "hd_720p":
        if has_ffmpeg:
            opts["format"] = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            opts["format_sort"] = ["vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "best[height<=720][ext=mp4]/best[height<=720]/best"
    elif quality_key == "sd_480p":
        if has_ffmpeg:
            opts["format"] = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            opts["format_sort"] = ["vcodec:h264", "acodec:aac", "ext:mp4:m4a"]
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = "best[height<=480][ext=mp4]/best[height<=480]/best"
    else:
        opts["format"] = "bestvideo+bestaudio/best" if has_ffmpeg else "best"
        if has_ffmpeg:
            opts["merge_output_format"] = "mp4"

    final_filepath: Optional[Path] = None

    def _progress_hook(d: dict[str, Any]) -> None:
        nonlocal final_filepath
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelledError("Descarga cancelada por el usuario.")

        status = d.get("status")
        if status == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0

            # Calcular porcentaje fiable
            if total and total > 0:
                percent = min(1.0, max(0.0, float(downloaded) / float(total)))
            else:
                frag_idx = d.get("fragment_index")
                frag_cnt = d.get("fragment_count")
                if frag_idx and frag_cnt and frag_cnt > 0:
                    percent = min(1.0, max(0.0, float(frag_idx) / float(frag_cnt)))
                else:
                    percent = 0.0

            speed = d.get("speed")
            speed_str = f"{format_bytes(speed)}/s" if speed else "Calculando..."
            eta = d.get("eta")
            eta_str = format_duration(eta) if eta is not None else "--:--"

            if progress_callback:
                progress_callback(
                    {
                        "stage": "downloading",
                        "percent": percent,
                        "downloaded_str": format_bytes(downloaded),
                        "total_str": format_bytes(total) if total else "?",
                        "speed_str": speed_str,
                        "eta_str": eta_str,
                        "message": f"Descargando... {int(percent * 100)}%",
                    }
                )

        elif status == "finished":
            filename = d.get("filename")
            if filename:
                final_filepath = Path(filename)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "processing",
                        "percent": 0.98,
                        "downloaded_str": "",
                        "total_str": "",
                        "speed_str": "",
                        "eta_str": "00:00",
                        "message": "Procesando y uniendo pistas de alta calidad...",
                    }
                )

    def _postprocessor_hook(d: dict[str, Any]) -> None:
        nonlocal final_filepath
        if cancel_event and cancel_event.is_set():
            raise DownloadCancelledError("Descarga cancelada por el usuario.")
        info_dict = d.get("info_dict") or {}
        filepath = info_dict.get("filepath") or info_dict.get("_filename")
        if filepath:
            final_filepath = Path(filepath)

    opts["progress_hooks"] = [_progress_hook]
    opts["postprocessor_hooks"] = [_postprocessor_hook]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(clean_url, download=True)
        if not info:
            raise RuntimeError("No se pudo descargar el video.")

        if "entries" in info and info["entries"]:
            entries = [e for e in info["entries"] if e]
            if entries:
                info = entries[0]

        # Resolver la ruta exacta del archivo descargado
        requested_downloads = info.get("requested_downloads") or []
        if requested_downloads and requested_downloads[0].get("filepath"):
            final_filepath = Path(requested_downloads[0]["filepath"])
        elif not final_filepath:
            prepared = Path(ydl.prepare_filename(info))
            if quality_key == "audio_mp3" and has_ffmpeg:
                mp3_candidate = prepared.with_suffix(".mp3")
                if mp3_candidate.exists():
                    final_filepath = mp3_candidate
            if not final_filepath:
                mp4_candidate = prepared.with_suffix(".mp4")
                if mp4_candidate.exists():
                    final_filepath = mp4_candidate
                else:
                    final_filepath = prepared

        title = (
            info.get("title")
            or info.get("description", "")[:70]
            or f"Video_{info.get('id', 'descarga')}"
        ).strip()
        uploader = (
            info.get("uploader")
            or info.get("channel")
            or info.get("creator")
            or info.get("uploader_id")
            or "Creador desconocido"
        )
        duration = info.get("duration")
        thumbnail = info.get("thumbnail")
        platform = detect_platform(info.get("webpage_url") or clean_url)

        metadata = VideoMetadata(
            url=clean_url,
            title=title,
            uploader=str(uploader),
            duration_seconds=float(duration) if duration is not None else None,
            duration_str=format_duration(duration),
            thumbnail_url=thumbnail,
            platform=platform,
            view_count=info.get("view_count"),
            webpage_url=info.get("webpage_url") or clean_url,
        )

    if not final_filepath or not final_filepath.exists():
        # Buscar el archivo más reciente en la carpeta de salida como respaldo seguro
        files = sorted(output_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if files:
            final_filepath = files[0]
        else:
            raise FileNotFoundError("La descarga finalizó pero no se encontró el archivo generado.")

    # Si es una descarga de video (no solo audio), garantizar que el códec sea H.264 (avc1) + AAC-LC
    # para que el Reproductor de Windows Media, Linux, WhatsApp y móviles muestren video + audio.
    if quality_key != "audio_mp3" and has_ffmpeg:
        final_filepath = ensure_universal_mp4_compatibility(
            filepath=final_filepath,
            ffmpeg_path=ffmpeg_path,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            strip_audio=(quality_key == "mute_mp4"),
        )

    if progress_callback:
        progress_callback(
            {
                "stage": "completed",
                "percent": 1.0,
                "downloaded_str": format_bytes(final_filepath.stat().st_size),
                "total_str": format_bytes(final_filepath.stat().st_size),
                "speed_str": "Completado",
                "eta_str": "00:00",
                "message": "¡Descarga completada con éxito!",
            }
        )

    return final_filepath, metadata


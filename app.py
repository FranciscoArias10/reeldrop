"""
reeldrop — interfaz minimalista inspirada en cobalt (cobalt.canine.tools)
Un solo input inteligente con detección automática de plataforma (YouTube, TikTok, IG Reels, X, etc.),
compatible con Windows y Linux.
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any, Optional

import customtkinter as ctk
from PIL import Image

from downloader import (
    BROWSER_COOKIE_OPTIONS,
    DownloadCancelledError,
    VideoMetadata,
    detect_platform,
    download_video,
    format_bytes,
    get_default_download_dir,
    get_ffmpeg_path,
    is_likely_video_url,
    open_path_cross_platform,
    strip_ansi,
)

# Paleta minimalista oscura estilo Cobalt
BG_MAIN = "#09090B"
BG_SURFACE = "#121215"
BG_ELEVATED = "#1A1A1F"
BG_HOVER = "#27272A"
BORDER_SUBTLE = "#232329"
BORDER_FOCUS = "#3F3F46"
TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#A1A1AA"
TEXT_MUTED = "#52525B"
ACCENT_WHITE = "#FAFAFA"
ACCENT_DARK_TEXT = "#09090B"
SUCCESS_COLOR = "#22C55E"
ERROR_COLOR = "#EF4444"

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
MASCOT_PATH = ASSETS_DIR / "mascota.png"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"

ctk.set_appearance_mode("Dark")


class CobaltMinimalApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title("reeldrop")
        self.geometry("660x490")
        self.minsize(520, 430)
        self.configure(fg_color=BG_MAIN)
        self._apply_window_icon()

        # Estado interno
        self.download_dir: Path = get_default_download_dir()
        self.mode: str = "auto"  # "auto" | "audio" | "mute"
        self.video_res: str = "reel_mp4"  # "reel_mp4" | "best_mp4" | "hd_720p"
        self.is_downloading: bool = False
        self.settings_visible: bool = False
        self.cancel_event: threading.Event = threading.Event()
        self.last_downloaded_file: Optional[Path] = None
        self.cookie_labels = list(BROWSER_COOKIE_OPTIONS.keys())
        self.mascot_image: Optional[ctk.CTkImage] = self._load_mascot()

        self._build_ui()

    def _apply_window_icon(self) -> None:
        try:
            if sys.platform.startswith("win") and ICON_ICO_PATH.exists():
                self.iconbitmap(str(ICON_ICO_PATH))
            elif ICON_PNG_PATH.exists():
                self._tk_icon = tk.PhotoImage(file=str(ICON_PNG_PATH))
                self.iconphoto(True, self._tk_icon)
        except Exception:
            pass

    def _load_mascot(self) -> Optional[ctk.CTkImage]:
        if MASCOT_PATH.exists():
            try:
                pil_img = Image.open(MASCOT_PATH).convert("RGBA")
                return ctk.CTkImage(
                    light_image=pil_img,
                    dark_image=pil_img,
                    size=(112, 112),
                )
            except Exception:
                return None
        return None

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # =====================================================================
        # BARRA SUPERIOR ULTRA DISCRETA (Carpeta y Ajustes opcionales)
        # =====================================================================
        top_nav = ctk.CTkFrame(self, fg_color="transparent")
        top_nav.grid(row=0, column=0, padx=20, pady=(14, 0), sticky="ew")
        top_nav.grid_columnconfigure(1, weight=1)

        self.folder_quick_btn = ctk.CTkButton(
            top_nav,
            text="📂 descargas",
            width=100,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=BG_ELEVATED,
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12),
            command=lambda: open_path_cross_platform(self.download_dir),
        )
        self.folder_quick_btn.grid(row=0, column=0, sticky="w")

        self.settings_btn = ctk.CTkButton(
            top_nav,
            text="⚙ ajustes",
            width=86,
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=BG_ELEVATED,
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(size=12),
            command=self.toggle_settings,
        )
        self.settings_btn.grid(row=0, column=2, sticky="e")

        # =====================================================================
        # CONTENEDOR CENTRAL (ESTILO COBALT: MASCOTA + 1 SOLO INPUT)
        # =====================================================================
        center_wrap = ctk.CTkFrame(self, fg_color="transparent")
        center_wrap.grid(row=1, column=0, padx=28, pady=6, sticky="nsew")
        center_wrap.grid_columnconfigure(0, weight=1)
        center_wrap.grid_rowconfigure(0, weight=1)
        center_wrap.grid_rowconfigure(6, weight=1)

        # 1. Mascota principal + píldora de plataforma autodetectada
        brand_frame = ctk.CTkFrame(center_wrap, fg_color="transparent")
        brand_frame.grid(row=1, column=0, pady=(0, 12))

        if self.mascot_image is not None:
            self.logo_label = ctk.CTkLabel(
                brand_frame,
                text="",
                image=self.mascot_image,
            )
        else:
            self.logo_label = ctk.CTkLabel(
                brand_frame,
                text="»",
                font=ctk.CTkFont(size=34, weight="bold"),
                text_color=TEXT_PRIMARY,
            )
        self.logo_label.pack(pady=(0, 6))

        self.platform_pill = ctk.CTkLabel(
            brand_frame,
            text="youtube • tiktok • instagram • x • +1000",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_MUTED,
            fg_color="transparent",
            corner_radius=10,
            padx=12,
            pady=3,
        )
        self.platform_pill.pack()

        # 2. EL ÚNICO INPUT (Barra unificada estilo Cobalt)
        self.input_bar = ctk.CTkFrame(
            center_wrap,
            fg_color=BG_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=BORDER_SUBTLE,
            height=52,
        )
        self.input_bar.grid(row=2, column=0, sticky="ew")
        self.input_bar.grid_columnconfigure(1, weight=1)

        self.link_icon_label = ctk.CTkLabel(
            self.input_bar,
            text="🔗",
            font=ctk.CTkFont(size=14),
            text_color=TEXT_MUTED,
            width=28,
        )
        self.link_icon_label.grid(row=0, column=0, padx=(14, 4), pady=10)

        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self._on_url_changed)

        self.url_entry = ctk.CTkEntry(
            self.input_bar,
            textvariable=self.url_var,
            placeholder_text="pega el enlace aquí",
            placeholder_text_color=TEXT_MUTED,
            fg_color="transparent",
            border_width=0,
            height=38,
            font=ctk.CTkFont(size=14),
            text_color=TEXT_PRIMARY,
        )
        self.url_entry.grid(row=0, column=1, padx=4, pady=7, sticky="ew")
        self.url_entry.bind("<Return>", lambda _e: self.on_submit())
        self.url_entry.bind("<FocusIn>", lambda _e: self._highlight_bar(True))
        self.url_entry.bind("<FocusOut>", lambda _e: self._highlight_bar(False))

        # Botones integrados dentro del mismo input (derecha)
        right_controls = ctk.CTkFrame(self.input_bar, fg_color="transparent")
        right_controls.grid(row=0, column=2, padx=(4, 8), pady=7)

        self.clear_btn = ctk.CTkButton(
            right_controls,
            text="✕",
            width=30,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.clear_url,
        )

        self.paste_btn = ctk.CTkButton(
            right_controls,
            text="pegar",
            width=66,
            height=34,
            corner_radius=9,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.paste_from_clipboard,
        )
        self.paste_btn.pack(side="left", padx=(0, 6))

        self.go_btn = ctk.CTkButton(
            right_controls,
            text=">>",
            width=48,
            height=34,
            corner_radius=9,
            fg_color=BG_ELEVATED,
            hover_color=ACCENT_WHITE,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_submit,
        )
        self.go_btn.pack(side="left")

        # 3. PÍLDORAS DE MODO ESTILO COBALT: [ ✨ auto ] [ ♪ audio ] [ 🔇 mute ]
        modes_row = ctk.CTkFrame(center_wrap, fg_color="transparent")
        modes_row.grid(row=3, column=0, pady=(12, 0))

        self.mode_buttons: dict[str, ctk.CTkButton] = {}
        mode_specs = [
            ("auto", "✨ auto"),
            ("audio", "♪ audio"),
            ("mute", "🔇 mute"),
        ]
        for key, label in mode_specs:
            btn = ctk.CTkButton(
                modes_row,
                text=label,
                width=88,
                height=32,
                corner_radius=16,
                border_width=1,
                font=ctk.CTkFont(size=12, weight="bold"),
                command=lambda k=key: self.set_mode(k),
            )
            btn.pack(side="left", padx=4)
            self.mode_buttons[key] = btn

        self._refresh_mode_pills()

        # 4. GAVETA OPCIONAL DE AJUSTES (Oculta por defecto)
        self.settings_drawer = ctk.CTkFrame(
            center_wrap,
            fg_color=BG_SURFACE,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self._build_settings_drawer()

        # 5. PÍLDORA MINIMALISTA DE ESTADO / PROGRESO / RESULTADO
        self.status_box = ctk.CTkFrame(
            center_wrap,
            fg_color=BG_SURFACE,
            corner_radius=12,
            border_width=1,
            border_color=BORDER_SUBTLE,
        )
        self.status_box.grid_columnconfigure(0, weight=1)

        status_top = ctk.CTkFrame(self.status_box, fg_color="transparent")
        status_top.grid(row=0, column=0, padx=14, pady=(10, 6), sticky="ew")
        status_top.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            status_top,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

        self.status_actions = ctk.CTkFrame(status_top, fg_color="transparent")
        self.status_actions.grid(row=0, column=1, padx=(8, 0), sticky="e")

        self.cancel_btn = ctk.CTkButton(
            self.status_actions,
            text="cancelar",
            width=68,
            height=24,
            corner_radius=7,
            fg_color=BG_ELEVATED,
            hover_color="#3F1D1D",
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            command=self.cancel_download,
        )

        self.open_file_btn = ctk.CTkButton(
            self.status_actions,
            text="▶ reproducir",
            width=88,
            height=26,
            corner_radius=7,
            fg_color=ACCENT_WHITE,
            hover_color="#E4E4E7",
            text_color=ACCENT_DARK_TEXT,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_last_file,
        )

        self.open_dir_btn = ctk.CTkButton(
            self.status_actions,
            text="carpeta",
            width=64,
            height=26,
            corner_radius=7,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            command=self._reveal_last_file,
        )

        self.progress_bar = ctk.CTkProgressBar(
            self.status_box,
            height=4,
            corner_radius=2,
            fg_color=BG_ELEVATED,
            progress_color=ACCENT_WHITE,
        )
        self.progress_bar.set(0.0)

    def _build_settings_drawer(self) -> None:
        self.settings_drawer.grid_columnconfigure(1, weight=1)
        self.settings_drawer.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            self.settings_drawer,
            text="calidad",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=0, padx=(12, 6), pady=(10, 6), sticky="w")

        self.res_map = {
            "1080p compatible": "reel_mp4",
            "máxima (4k)": "best_mp4",
            "720p ligero": "hd_720p",
        }
        self.res_menu = ctk.CTkOptionMenu(
            self.settings_drawer,
            values=list(self.res_map.keys()),
            height=28,
            corner_radius=7,
            fg_color=BG_ELEVATED,
            button_color=BG_HOVER,
            button_hover_color=BORDER_FOCUS,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=11),
            command=self._on_res_changed,
        )
        self.res_menu.set("1080p compatible")
        self.res_menu.grid(row=0, column=1, padx=(0, 12), pady=(10, 6), sticky="ew")

        ctk.CTkLabel(
            self.settings_drawer,
            text="cookies",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
        ).grid(row=0, column=2, padx=(0, 6), pady=(10, 6), sticky="w")

        self.cookie_menu = ctk.CTkOptionMenu(
            self.settings_drawer,
            values=self.cookie_labels,
            height=28,
            corner_radius=7,
            fg_color=BG_ELEVATED,
            button_color=BG_HOVER,
            button_hover_color=BORDER_FOCUS,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=11),
        )
        self.cookie_menu.set(self.cookie_labels[0])
        self.cookie_menu.grid(row=0, column=3, padx=(0, 12), pady=(10, 6), sticky="ew")

        folder_row = ctk.CTkFrame(self.settings_drawer, fg_color="transparent")
        folder_row.grid(row=1, column=0, columnspan=4, padx=12, pady=(2, 10), sticky="ew")
        folder_row.grid_columnconfigure(0, weight=1)

        self.dir_label = ctk.CTkLabel(
            folder_row,
            text=f"guardar en: {self.download_dir}",
            font=ctk.CTkFont(size=11),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.dir_label.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            folder_row,
            text="cambiar carpeta",
            width=106,
            height=24,
            corner_radius=6,
            fg_color=BG_ELEVATED,
            hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(size=11),
            command=self.choose_download_dir,
        ).grid(row=0, column=1, padx=(8, 0))

    # =========================================================================
    # COMPORTAMIENTO INTERACTIVO
    # =========================================================================
    def _highlight_bar(self, focused: bool) -> None:
        url = self.url_var.get().strip()
        if url:
            info = detect_platform(url)
            if info.key not in ("none", "unknown"):
                self.input_bar.configure(border_color=info.color if focused else BORDER_FOCUS)
                return
        self.input_bar.configure(border_color=BORDER_FOCUS if focused else BORDER_SUBTLE)

    def _on_url_changed(self, *_args: Any) -> None:
        url = self.url_var.get().strip()
        info = detect_platform(url)

        if not url:
            self.platform_pill.configure(
                text="youtube • tiktok • instagram • x • +1000",
                fg_color="transparent",
                text_color=TEXT_MUTED,
            )
            self.link_icon_label.configure(text="🔗", text_color=TEXT_MUTED)
            self.input_bar.configure(border_color=BORDER_SUBTLE)
            self.clear_btn.pack_forget()
            self.paste_btn.pack_forget()
            self.go_btn.pack_forget()
            self.paste_btn.pack(side="left", padx=(0, 6))
            self.go_btn.configure(fg_color=BG_ELEVATED, text_color=TEXT_SECONDARY, hover_color=BG_HOVER)
            self.go_btn.pack(side="left")
            return

        self.platform_pill.configure(
            text=f"{info.badge} detectado" if info.key != "unknown" else info.badge,
            fg_color=BG_ELEVATED,
            text_color=info.color if info.key != "none" else TEXT_SECONDARY,
        )
        icon_symbol = info.badge.split(" ")[0] if " " in info.badge else "🔗"
        self.link_icon_label.configure(text=icon_symbol, text_color=info.color)
        self.input_bar.configure(border_color=info.color if info.key != "unknown" else BORDER_FOCUS)

        self.paste_btn.pack_forget()
        self.clear_btn.pack_forget()
        self.go_btn.pack_forget()
        self.clear_btn.pack(side="left", padx=(0, 6))
        self.go_btn.configure(fg_color=ACCENT_WHITE, text_color=ACCENT_DARK_TEXT, hover_color="#E4E4E7")
        self.go_btn.pack(side="left")

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        self._refresh_mode_pills()

    def _refresh_mode_pills(self) -> None:
        for key, btn in self.mode_buttons.items():
            if key == self.mode:
                btn.configure(
                    fg_color=ACCENT_WHITE,
                    text_color=ACCENT_DARK_TEXT,
                    border_color=ACCENT_WHITE,
                    hover_color="#E4E4E7",
                )
            else:
                btn.configure(
                    fg_color=BG_SURFACE,
                    text_color=TEXT_SECONDARY,
                    border_color=BORDER_SUBTLE,
                    hover_color=BG_ELEVATED,
                )

    def _on_res_changed(self, label: str) -> None:
        self.video_res = self.res_map.get(label, "reel_mp4")

    def toggle_settings(self) -> None:
        self.settings_visible = not self.settings_visible
        if self.settings_visible:
            self.settings_drawer.grid(row=4, column=0, pady=(12, 0), sticky="ew")
            self.settings_btn.configure(text_color=TEXT_PRIMARY, fg_color=BG_ELEVATED)
        else:
            self.settings_drawer.grid_forget()
            self.settings_btn.configure(text_color=TEXT_MUTED, fg_color="transparent")

    def choose_download_dir(self) -> None:
        selected = filedialog.askdirectory(initialdir=str(self.download_dir), title="Carpeta de descargas")
        if selected:
            self.download_dir = Path(selected)
            self.download_dir.mkdir(parents=True, exist_ok=True)
            self.dir_label.configure(text=f"guardar en: {self.download_dir}")

    def _read_clipboard(self) -> str:
        try:
            return (self.clipboard_get() or "").strip()
        except Exception:
            return ""

    def paste_from_clipboard(self) -> Optional[str]:
        clip = self._read_clipboard()
        if not clip:
            self._show_status("el portapapeles está vacío", color=TEXT_SECONDARY, show_bar=False)
            return None
        self.url_var.set(clip)
        self.url_entry.focus_set()
        self.url_entry.icursor("end")
        return clip

    def clear_url(self) -> None:
        self.url_var.set("")
        self.url_entry.focus_set()

    # =========================================================================
    # EJECUCIÓN DE DESCARGA
    # =========================================================================
    def on_submit(self) -> None:
        if self.is_downloading:
            return

        url = self.url_var.get().strip()
        if not url:
            clip = self._read_clipboard()
            if is_likely_video_url(clip):
                self.url_var.set(clip)
                url = clip
            else:
                self._show_status("pega un enlace primero", color=TEXT_SECONDARY, show_bar=False)
                return

        info = detect_platform(url)
        if info.key == "unknown":
            self._show_status("enlace no válido — asegúrate de copiar la url completa", color=ERROR_COLOR, show_bar=False)
            return

        self.is_downloading = True
        self.cancel_event.clear()
        self.go_btn.configure(state="disabled", text="•••")

        if self.mode == "audio":
            quality_key = "audio_mp3"
        elif self.mode == "mute":
            quality_key = "mute_mp4"
        else:
            quality_key = self.video_res

        browser_cookies = BROWSER_COOKIE_OPTIONS.get(self.cookie_menu.get())
        target_dir = self.download_dir

        self._prepare_downloading_status(f"conectando con {info.name.lower()}...")

        def _on_progress(data: dict[str, Any]) -> None:
            self.after(0, lambda: self._update_progress(data, info.name.lower()))

        def _worker() -> None:
            try:
                filepath, metadata = download_video(
                    url=url,
                    output_dir=target_dir,
                    quality_key=quality_key,
                    browser_cookies=browser_cookies,
                    progress_callback=_on_progress,
                    cancel_event=self.cancel_event,
                )
                self.after(0, lambda: self._on_success(filepath, metadata))
            except DownloadCancelledError:
                self.after(0, self._on_cancelled)
            except Exception as exc:
                err = strip_ansi(str(exc))
                self.after(0, lambda: self._on_error(err))

        threading.Thread(target=_worker, daemon=True).start()

    def cancel_download(self) -> None:
        if self.is_downloading:
            self.cancel_event.set()
            self.cancel_btn.configure(state="disabled")
            self.status_label.configure(text="cancelando...", text_color=TEXT_MUTED)

    def _show_status(self, text: str, color: str = TEXT_SECONDARY, show_bar: bool = False) -> None:
        self.status_box.grid(row=5, column=0, pady=(14, 0), sticky="ew")
        self.status_label.configure(text=text, text_color=color)
        self.cancel_btn.pack_forget()
        self.open_file_btn.pack_forget()
        self.open_dir_btn.pack_forget()
        if show_bar:
            self.progress_bar.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")
        else:
            self.progress_bar.grid_forget()

    def _prepare_downloading_status(self, text: str) -> None:
        self._show_status(text, color=TEXT_PRIMARY, show_bar=True)
        self.progress_bar.configure(progress_color=ACCENT_WHITE)
        self.progress_bar.set(0.03)
        self.cancel_btn.configure(state="normal")
        self.cancel_btn.pack(side="left")

    def _update_progress(self, data: dict[str, Any], platform_name: str) -> None:
        pct = float(data.get("percent", 0.0))
        stage = data.get("stage", "downloading")
        self.progress_bar.set(pct)

        if stage == "processing":
            msg = data.get("message") or "procesando mp4..."
            self.status_label.configure(text=msg.lower(), text_color=TEXT_PRIMARY)
        else:
            speed = data.get("speed_str") or ""
            speed_part = f" • {speed.lower()}" if speed and "calculando" not in speed.lower() else ""
            self.status_label.configure(
                text=f"descargando de {platform_name} • {int(pct * 100)}%{speed_part}",
                text_color=TEXT_PRIMARY,
            )

    def _on_success(self, filepath: Path, metadata: VideoMetadata) -> None:
        self.last_downloaded_file = filepath
        self._reset_submit_btn()

        size_str = format_bytes(filepath.stat().st_size) if filepath.exists() else ""
        short_title = metadata.title if len(metadata.title) <= 44 else f"{metadata.title[:41]}..."
        self._show_status(
            f"✓ {short_title} ({size_str})",
            color=SUCCESS_COLOR,
            show_bar=False,
        )
        self.open_file_btn.pack(side="left", padx=(0, 6))
        self.open_dir_btn.pack(side="left")
        self.url_var.set("")

    def _on_cancelled(self) -> None:
        self._reset_submit_btn()
        self._show_status("descarga cancelada", color=TEXT_MUTED, show_bar=False)

    def _on_error(self, error_msg: str) -> None:
        self._reset_submit_btn()
        lower = error_msg.lower()
        if any(k in lower for k in ("login", "cookie", "private", "sign in")):
            msg = "requiere sesión — abre '⚙ ajustes' y elige las cookies de tu navegador"
        else:
            last_line = error_msg.splitlines()[-1] if error_msg.splitlines() else error_msg
            msg = f"error: {last_line[:68].lower()}"
        self._show_status(msg, color=ERROR_COLOR, show_bar=False)

    def _reset_submit_btn(self) -> None:
        self.is_downloading = False
        has_url = bool(self.url_var.get().strip())
        self.go_btn.configure(
            state="normal",
            text=">>",
            fg_color=ACCENT_WHITE if has_url else BG_ELEVATED,
            text_color=ACCENT_DARK_TEXT if has_url else TEXT_SECONDARY,
        )

    def _open_last_file(self) -> None:
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            open_path_cross_platform(self.last_downloaded_file, reveal_in_folder=False)

    def _reveal_last_file(self) -> None:
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            open_path_cross_platform(self.last_downloaded_file, reveal_in_folder=True)
        else:
            open_path_cross_platform(self.download_dir, reveal_in_folder=False)


def run_self_test() -> int:
    print("=== reeldrop self-test ===")
    app = CobaltMinimalApp()
    app.update_idletasks()

    assert app.mascot_image is not None, "La mascota principal (Opción 2) no se cargó"
    assert ICON_ICO_PATH.exists() and ICON_PNG_PATH.exists(), "Iconos de ventana no encontrados"
    print(f"[OK] Mascota principal activa: {MASCOT_PATH}")
    print(f"[OK] Iconos de ventana (Windows/Linux): {ICON_ICO_PATH.name}, {ICON_PNG_PATH.name}")

    app.url_var.set("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    app.update_idletasks()
    assert app.platform_pill.cget("text") == "⚡ youtube shorts detectado"

    app.destroy()
    print("[OK] Aplicación verificada correctamente.")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(run_self_test())

    app = CobaltMinimalApp()
    app.mainloop()

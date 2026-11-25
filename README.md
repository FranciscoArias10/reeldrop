# ⚡ ReelDrop — Descargador Universal de Reels, Shorts, TikTok y Redes Sociales

> ⚠️ **Proyecto educativo y de pruebas.** Úsalo solo con contenido propio o con permiso, y respeta los derechos de autor y los términos de cada plataforma. Lee el [DISCLAIMER.md](DISCLAIMER.md) (en inglés).

Aplicación de escritorio multiplataforma (**Windows** y **Linux**) con interfaz gráfica moderna construida en **Python + CustomTkinter + yt-dlp + FFmpeg integrado**.

Diseñada especialmente para descargar videos cortos (**Instagram Reels, TikTok, YouTube Shorts, Facebook Reels, X/Twitter, Reddit, Twitch Clips, Pinterest, Threads**) y videos completos de **+1000 plataformas** con **1 solo clic**.

---

## ✨ Características Principales

- **⚡ Pegar y Descargar en 1 Clic**: Lee automáticamente el enlace copiado en tu portapapeles y comienza la descarga al instante.
- **🎯 Detección Automática de Red Social**: Identifica visualmente si pegaste un enlace de **TikTok**, **Instagram Reel**, **YouTube Short**, **Facebook Reel**, **X / Twitter**, **Reddit**, **Twitch**, etc.
- **📱 Formato MP4 Optimizado para Reels/Shorts**: Prioriza códecs universales (`H.264 + AAC` en contenedor `.mp4`) para que los videos descargados se reproduzcan sin problemas en WhatsApp, Telegram, móviles, Windows y Linux.
- **🎬 FFmpeg Integrado Automáticamente**: Incluye `imageio-ffmpeg` para unir pistas de video Full HD / 4K y extraer audio MP3 sin necesidad de instalar FFmpeg manualmente en el sistema.
- **🍪 Soporte de Cookies de Navegador (Opcional)**: Permite usar la sesión de Chrome, Edge, Firefox o Brave para descargar Reels o videos con restricción de inicio de sesión.
- **🖥️ 100% Compatible con Windows y Linux**: Aperturas nativas de archivos y carpetas (`Explorer` en Windows / `xdg-open` en Linux).

---

## 🚀 Cómo Ejecutar

### En Windows
1. Haz doble clic sobre **`ejecutar_windows.bat`**
   *(o ejecuta en terminal)*:
   ```powershell
   py app.py
   ```

### En Linux (Ubuntu / Debian / Fedora / Arch)
1. Asegúrate de tener `python3-tk` instalado (en Ubuntu/Debian: `sudo apt install python3-tk python3-venv`).
2. Da permisos de ejecución y lanza el script (crea el entorno e instala dependencias automáticamente):
   ```bash
   chmod +x ejecutar_linux.sh
   ./ejecutar_linux.sh
   ```


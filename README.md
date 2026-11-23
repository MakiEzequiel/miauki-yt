<p align="center">
  <img src="docs/img/portada-miauki.png" alt="Miauki YT" width="100%">
</p>

<p align="center">
  <b>Miauki YT</b> — The friendly downloader for everyone.
  Download videos, music, photos and stories from your favorite sites with a single, simple app.
</p>

---

## Why Miauki?

Miauki was born as a personal project: a downloader that just *works*, without menus full of technical jargon, without ugly interfaces, without asking you to be an expert.

Then I realized it could be useful for many more people. So I polished it, made it beautiful, translated it, and gave it to the community for free — because I believe good software should be **free, simple, and pleasant** for everyone: your grandma, your neighbor, your teacher, you.

If you use it and like it, that's already a win. If you want to help me keep improving it (better models, new sites, more features), there's an optional support section at the bottom. Every bit helps, but nothing is required.

## What it does

Paste a link, press **Analyze**, and Miauki shows you the video, song, photo or story with its qualities. Choose one and it downloads to your folder. That's it.

| Supported | Content |
|---|---|
| **YouTube** | Videos, Shorts, playlists, YouTube Music |
| **TikTok** | Videos, photos (with session/cookies) |
| **Instagram** | Posts, reels, stories, highlights |
| **Facebook** | Videos, reels (photos need session/cookies) |
| **X / Twitter** | Videos, multiple photos, NSFW (with cookies) |
| **Snapchat** | Spotlight and stories |
| **Google Images** | Direct images and share.google links |
| **Others** | Vimeo, Dailymotion, Reddit, Pinterest, SoundCloud and more (via yt-dlp) |

## Features

- **Friendly interface** in English and Spanish (switch in Settings).
- **Simple by design**: one field, one button, clear results. No technical knowledge needed.
- **Download queue** with pause / resume / cancel.
- **Cookies**: `.txt` (Netscape) and `.json` files, or pick a browser (Chrome, Edge, Firefox, Brave, Chromium, Opera, Vivaldi) for content that needs a login.
- **Qualities**: video up to 4K/8K, music 320, original image (depending on the site).
- **Privacy**: no telemetry. Everything stays on your PC.
- Initial window 1420×840, resizable.

## Download

| Version | Download | SHA-256 |
|---|---|---|
| **v1.0.0** | [Miauki.YT.v1.0.0.exe](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.exe) | `2f976c8aa1c80d9677348d157734908eb9dbc034e0fcc84449d1d621c3bc9503` |
| **v1.0.0 (full ZIP)** | [Miauki.YT.v1.0.0.-.Windows.zip](https://github.com/MakiEzequiel/miauki-yt/releases/download/v1.0.0/Miauki.YT.v1.0.0.-.Windows.zip) | `c47465d28c81f317a14e9f32db66e7106db88a981a3ddab9fe23d074240dd818` |

> Windows SmartScreen may warn when opening the `.exe` for the first time: that's normal for unsigned programs. Click "More info → Run anyway".

The `.exe` is fully self-contained (ffmpeg, yt-dlp and the interface are embedded). No installation needed.

## Requirements

- Windows 10/11 (with WebView2 Runtime; Miauki installs it automatically if missing).
- For `--selftest` or running from source: Python 3.11+.

## From the source code

```bash
pip install -r requirements.txt
python app.py            # open the app
python app.py --selftest # check ffmpeg, yt-dlp, WebView2 and the interface
python -m pytest         # test suite
```

## Documentation

- `docs/DECISIONES.md` — design and architecture decisions.
- `docs/PENDIENTES.md` — backlog and known limitations.
- `docs/DISTRIBUCION.md` — how to build the `.exe`.

## Support

Miauki is free, open source, and has no ads. If you enjoy it and want to help me keep improving it (paying for better development tools, new sites, translations), any contribution is deeply appreciated:

- **PayPal**: [paypal.me/ezequielgottwald](https://www.paypal.com/paypalme/ezequielgottwald)
- **Bank alias (Argentina, Naranja X)**: `makiezequiel.naranja`
- **USDT (Tron TRC20)**: `TPQcvumqfVcxWgHHveUSgLy4CVBYsMjZrg`

Thank you for reading, for using it, and for being part of this little project. 🐱

## License

MIT — see [LICENSE](LICENSE). Miauki bundles yt-dlp, ffmpeg and other third-party libraries (details in `docs/LICENCIAS_TERCEROS.md`).

---

**Español:** [README.es.md](README.es.md)

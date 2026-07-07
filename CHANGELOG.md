# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-07-07

### Added
- **Sessionid mode** — instagrapi login via browser cookie (no password, no 2FA)
- **Setup wizard** (`--setup`) — opens browser, polls for login, saves cookie to config
- **Config management** — `~/.ig-downloader/config.json`, auto-detected on each run
- **Chrome cookie extraction** — DPAPI + AES-GCM decryption for automatic sessionid retrieval
- Three-way source priority: `--sessionid` flag > `SESSIONID` env var > config file > Chrome cookies
- `--username` / `-u` flag for target Instagram handle
- `--version` flag
- Full carousel extraction via `media_info()` for ALL posts (no GQL cutoff)

### Changed
- Script auto-detects mode: sessionid (config) → setup → Apify legacy → help
- `instagrapi` is now a hard dependency for sessionid mode
- Output folder structure uses `post_info.txt` with `relation: own_post` field
- `--profile` flag renamed to `-u`/`--username`

### Removed
- `--no-instagrapi` flag (no longer needed — instagrapi is always available in sessionid mode)

## [1.1.0] - 2026-07-07

### Added
- Hybrid carousel extraction via `instagrapi` GQL (no login, no cookies)
- `--no-instagrapi` flag to disable GQL enhancement
- `InstagrapiHelper` class: lazy-init `Client`, `get_carousel_images()`, `download_url()` via `public.get()` to bypass CDN 403
- GQL stats tracking (hits/misses) in download summary
- Full carousel downloads — all images, not just thumbnail

### Changed
- Carousel processing: try GQL first (20s timeout), fallback to Apify thumbnail on failure
- Download method: use `instagrapi`'s browser-like client for CDN URLs from `fbcdn.net`
- `requirements.txt` now includes `instagrapi>=2.0.0`

### Fixed
- `fbcdn.net` CDN URLs returning 403 with plain `requests` — now use `instagrapi` `public.get()` which has proper browser headers

## [1.0.0] - 2026-07-06

### Added
- Initial release
- Apify-based Instagram media downloader
- Two input modes: `--dataset` (Apify API) and `--toon-file` (MCP export)
- Filters: `--date-start/--end`, `--type`, `--own-only`, `--mentions-only`
- Output organization: `YYYY-MM-DD/shortcode/` with `post_info.txt`
- Flat output mode: `--flat`
- Reel download (MP4) + thumbnail
- Carousel/photo download (single thumbnail JPG per post)
- Retry logic for failed downloads
- SSL verification toggle (`--no-verify`)

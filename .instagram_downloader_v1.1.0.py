#!/usr/bin/env python3
"""
Instagram Downloader — Apify + instagrapi hybrid media downloader
==================================================================
Downloads all media (reels MP4, carousels JPG, photos JPG) from an
Instagram profile using Apify Actor data as the primary source and
instagrapi GQL as an enhancement for full carousel extraction.

Two input modes:
  1. Apify Dataset API (requires APIFY_API_TOKEN)
  2. Toon/YAML file from MCP tool output (no token needed)

For carousels:
  - Tries instagrapi GQL first (no login, recent posts only ~3 weeks)
  - If GQL succeeds: downloads ALL carousel images (_01.jpg ... _0N.jpg)
  - If GQL fails: falls back to Apify thumbnail_url (first image only)

For reels/photos:
  - Uses Apify dataset URLs directly (requests works fine)

Usage:
  # Mode 1: Direct from Apify dataset (with API token)
  python instagram_downloader.py \\
      --dataset <DATASET_ID> \\
      --api-token apify_api_xxx \\
      --profile username \\
      --date-start YYYY-MM-DD --date-end YYYY-MM-DD \\
      --output ./instagram_downloads

  # Mode 2: From MCP toon-file (no token)
  python instagram_downloader.py \\
      --toon-file ./dataset_output.txt \\
      --profile username \\
      --date-start YYYY-MM-DD --date-end YYYY-MM-DD \\
      --output ./instagram_downloads

  # Filter only reels
  python instagram_downloader.py \\
      --toon-file ./data.txt \\
      --profile username \\
      --type reel \\
      --output ./reels_only

  # Own posts only (filter mentions)
  python instagram_downloader.py \\
      --toon-file ./data.txt \\
      --profile username \\
      --own-only \\
      --output ./own_posts
"""
import os, sys, re, json, argparse
from datetime import datetime, timezone, date
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)

# ── Optional: instagrapi for carousel full extraction ──────────
try:
    from instagrapi import Client as InstaClient
    from instagrapi.exceptions import ClientError, LoginRequired
    HAS_INSTAGRAPI = True
except ImportError:
    HAS_INSTAGRAPI = False

# ── UTF-8 output ──────────────────────────────────────────────
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ── Constants ─────────────────────────────────────────────────
APIFY_API_BASE = "https://api.apify.com/v2"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)
INSTA_HEADERS = {
    "User-Agent": DEFAULT_USER_AGENT,
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.instagram.com/",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "no-cors",
    "Sec-Fetch-Dest": "image",
}


# ═══════════════════════════════════════════════════════════════
#  INSTAGRAPI HELPER
# ═══════════════════════════════════════════════════════════════

class InstagrapiHelper:
    """Lazy wrapper around instagrapi for GQL carousel extraction + CDN download."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = InstaClient()
        return self._client

    def is_available(self) -> bool:
        return HAS_INSTAGRAPI

    def get_carousel_images(self, shortcode: str, timeout_s: int = 20) -> list[str] | None:
        """Fetch all carousel image URLs via instagrapi GQL (no login).
        Returns a list of fbcdn.net URLs, or None on failure."""
        if not self.is_available():
            return None
        try:
            import signal
            signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError))
            signal.alarm(timeout_s)
        except (AttributeError, ValueError):
            pass  # not POSIX or Windows

        try:
            pk = self.client.media_pk_from_code(shortcode)
            info = self.client.media_info_gql(pk)

            if info.media_type == 8 and hasattr(info, "resources") and info.resources:
                # Carousel: extract all image URLs
                images = []
                for r in info.resources:
                    url = str(r.thumbnail_url) if r.thumbnail_url else None
                    if url:
                        images.append(url)
                return images if images else None

            # Not a carousel or no resources — might be a single photo
            if info.thumbnail_url:
                return [str(info.thumbnail_url)]

            return None

        except Exception:
            return None
        finally:
            try:
                signal.alarm(0)
            except (AttributeError, ValueError):
                pass

    def download_url(self, url: str, filepath: str) -> bool:
        """Download a CDN URL using instagrapi's browser-like HTTP session.
        Required for fbcdn.net URLs which block requests.get()."""
        if not self.is_available():
            return False
        try:
            resp = self.client.public.get(url, timeout=60, stream=True)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception:
            pass
        return False


# ═══════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════

def build_parser():
    p = argparse.ArgumentParser(
        description="Download Instagram media via Apify dataset + optional instagrapi enhancement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input sources (mutually exclusive)
    src = p.add_argument_group("Input Sources (choose one)")
    src.add_argument("--dataset", metavar="ID",
        help="Apify dataset ID (e.g. 11VioLZi3oOUkyc5h). Requires --api-token.")
    src.add_argument("--api-token", metavar="KEY",
        help="Apify API token (required with --dataset).")
    src.add_argument("--toon-file", metavar="PATH",
        help="Path to a toon/YAML file from MCP get-dataset-items output.")

    # Filters
    flt = p.add_argument_group("Filters")
    flt.add_argument("--profile", metavar="HANDLE", default=None,
        help="Target Instagram handle. Used to classify OWN vs MENTION.")
    flt.add_argument("--date-start", metavar="YYYY-MM-DD", default=None,
        help="Earliest post date (inclusive).")
    flt.add_argument("--date-end", metavar="YYYY-MM-DD", default=None,
        help="Latest post date (inclusive).")
    flt.add_argument("--type", metavar="T", choices=["reel","carousel","photo","all"],
        default="all", help="Filter by post type (default: all).")
    flt.add_argument("--own-only", action="store_true",
        help="Download only posts authored by --profile (exclude mentions).")
    flt.add_argument("--mentions-only", action="store_true",
        help="Download only mentions from other accounts.")

    # Output
    out = p.add_argument_group("Output")
    out.add_argument("--output", "-o", metavar="DIR", default="instagram_downloads",
        help="Output directory (default: ./instagram_downloads).")
    out.add_argument("--flat", action="store_true",
        help="Flatten: single folder instead of YYYY-MM-DD/shortcode/.")

    # Instagrapi control
    p.add_argument("--no-instagrapi", action="store_true",
        help="Skip instagrapi carousel enhancement (use Apify thumbnails only).")

    # Misc
    p.add_argument("--no-verify", action="store_true",
        help="Skip SSL verification (not recommended).")

    return p


# ═══════════════════════════════════════════════════════════════
#  DATA FETCHING
# ═══════════════════════════════════════════════════════════════

def fetch_from_api(dataset_id: str, api_token: str) -> list[dict]:
    """Fetch dataset items from Apify API directly."""
    url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items"
    resp = requests.get(url, params={"token": api_token}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def fetch_from_toon(filepath: str) -> list[dict]:
    """Parse the toon/YAML-like format produced by MCP get-dataset-items."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    items_raw = re.split(r"\n  - ", content)
    items = []

    for item_str in items_raw:
        item = {}
        for line in item_str.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                line = line[2:]
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()

            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value in ("null", "~", ""):
                value = None

            if "." in key:
                parts = key.split(".")
                if parts[0] not in item or not isinstance(item[parts[0]], dict):
                    item[parts[0]] = {}
                item[parts[0]][parts[1]] = value
            else:
                item[key] = value

        if item.get("shortcode"):
            items.append(item)

    return items


# ═══════════════════════════════════════════════════════════════
#  DATA NORMALISATION
# ═══════════════════════════════════════════════════════════════

def normalize_item(raw: dict) -> dict:
    """Normalise a raw item (from API JSON or parsed toon) into consistent form."""
    author_handle = raw.get("author_handle")
    if not author_handle and isinstance(raw.get("author"), dict):
        author_handle = raw["author"].get("handle")

    video_url = raw.get("video_url_no_watermark")
    if not video_url and isinstance(raw.get("video"), dict):
        video_url = raw["video"].get("url_no_watermark")

    created_at_str = raw.get("created_at", "")
    created_at = None
    if created_at_str:
        try:
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    return {
        "shortcode": raw.get("shortcode", ""),
        "type": raw.get("type", "unknown"),
        "created_at": created_at,
        "created_at_str": created_at_str,
        "author_handle": author_handle or "unknown",
        "video_url": video_url,
        "thumbnail_url": raw.get("thumbnail_url"),
        "raw": raw,
    }


# ═══════════════════════════════════════════════════════════════
#  DOWNLOAD
# ═══════════════════════════════════════════════════════════════

def download_file(url: str, filepath: str, *,
                  verify: bool = True,
                  insta_helper: InstagrapiHelper | None = None,
                  max_retries: int = 3) -> bool:
    """Download a file with retries. Uses instagrapi for fbcdn.net URLs when available."""
    for attempt in range(1, max_retries + 1):
        try:
            # ── Try instagrapi first (handles fbcdn.net 403s) ──
            if insta_helper and insta_helper.is_available():
                if insta_helper.download_url(url, filepath):
                    size_kb = os.path.getsize(filepath) / 1024
                    print(f"  [OK] {os.path.basename(filepath)} ({size_kb:.1f} KB)")
                    return True

            # ── Fallback: plain requests ──
            resp = requests.get(url, headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "*/*",
                "Referer": "https://www.instagram.com/",
            }, timeout=60, stream=True, verify=verify)

            if resp.status_code == 200:
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                size_kb = os.path.getsize(filepath) / 1024
                print(f"  [OK] {os.path.basename(filepath)} ({size_kb:.1f} KB)")
                return True
            else:
                print(f"  [HTTP {resp.status_code}] {urlparse(url).path[-40:]}")

        except requests.RequestException as e:
            if attempt < max_retries:
                print(f"  [RETRY {attempt}/{max_retries}] {e}")
            else:
                print(f"  [FAIL] {e}")
    return False


# ═══════════════════════════════════════════════════════════════
#  PROCESSING
# ═══════════════════════════════════════════════════════════════

def process_items(items: list[dict], args: argparse.Namespace,
                  insta_helper: InstagrapiHelper | None = None):
    """Apply filters and download media for matching items."""

    # ── Parse date range ──
    dt_start = dt_end = None
    if args.date_start:
        dt_start = datetime.combine(
            date.fromisoformat(args.date_start),
            datetime.min.time(), tzinfo=timezone.utc)
    if args.date_end:
        dt_end = datetime.combine(
            date.fromisoformat(args.date_end),
            datetime.max.time(), tzinfo=timezone.utc)

    # ── Normalise ──
    normed = [normalize_item(it) for it in items]

    # ── Filter ──
    filtered = []
    skipped_no_date = 0
    for item in normed:
        if not item["created_at"]:
            skipped_no_date += 1
            continue
        if dt_start and item["created_at"] < dt_start:
            continue
        if dt_end and item["created_at"] > dt_end:
            continue
        if args.type != "all" and item["type"] != args.type:
            continue
        if args.own_only and item["author_handle"] != args.profile:
            continue
        if args.mentions_only and item["author_handle"] == args.profile:
            continue
        filtered.append(item)

    if skipped_no_date:
        print(f"  ⚠ {skipped_no_date} items skipped (no valid date)\n")
    print(f"  {len(filtered)} posts match filters (out of {len(normed)} total)\n")

    # ── Stats ──
    stats = {"reel": 0, "carousel": 0, "photo": 0, "unknown": 0}
    dl_ok = 0
    dl_fail = 0
    dl_skip = 0
    gql_hits = 0
    gql_misses = 0

    for idx, item in enumerate(filtered):
        post_type = item["type"]
        shortcode = item["shortcode"]
        author = item["author_handle"]
        is_own = author == args.profile
        tag = "OWN" if is_own else "MENTION"

        stats[post_type] = stats.get(post_type, 0) + 1

        # ── Output path ──
        date_str = item["created_at"].strftime("%Y-%m-%d") if item["created_at"] else "no-date"
        if args.flat:
            post_dir = os.path.join(args.output)
        else:
            post_dir = os.path.join(args.output, date_str, shortcode)

        os.makedirs(post_dir, exist_ok=True)

        print(f"\n{idx+1}. {date_str} | {post_type.upper():8s} | {tag} | @{author} | {shortcode}")

        # ── Save post info ──
        info_path = os.path.join(post_dir, "post_info.txt")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"shortcode: {shortcode}\n")
            f.write(f"type: {post_type}\n")
            f.write(f"date: {item['created_at_str']}\n")
            f.write(f"author: {author}\n")
            if args.profile:
                f.write(f"relation: {'own_post' if is_own else 'mention'}\n")
            f.write(f"url: https://www.instagram.com/p/{shortcode}/\n")
            if item["video_url"]:
                f.write(f"video_url: {item['video_url']}\n")
            if item["thumbnail_url"]:
                f.write(f"thumbnail_url: {item['thumbnail_url']}\n")

        # ── Download media ──

        # REEL
        if post_type == "reel" and item["video_url"]:
            filepath = os.path.join(post_dir, f"{shortcode}.mp4")
            if os.path.isfile(filepath) and os.path.getsize(filepath) > 10000:
                print(f"  [SKIP] {shortcode}.mp4 exists")
                dl_skip += 1
            elif download_file(item["video_url"], filepath,
                               verify=not args.no_verify,
                               insta_helper=insta_helper):
                dl_ok += 1
            else:
                dl_fail += 1

            # Thumbnail for reels
            if item["thumbnail_url"]:
                thumb_path = os.path.join(post_dir, f"{shortcode}_thumb.jpg")
                if not (os.path.isfile(thumb_path) and os.path.getsize(thumb_path) > 1000):
                    download_file(item["thumbnail_url"], thumb_path,
                                  verify=not args.no_verify,
                                  insta_helper=insta_helper)

        # CAROUSEL — try instagrapi for all images
        elif post_type == "carousel":
            use_gql = (not args.no_instagrapi and insta_helper is not None
                       and insta_helper.is_available())
            carousel_urls = None

            if use_gql:
                carousel_urls = insta_helper.get_carousel_images(shortcode)
                if carousel_urls:
                    gql_hits += 1
                    print(f"  [GQL] {len(carousel_urls)} images from instagrapi")
                else:
                    gql_misses += 1
                    print(f"  [GQL] not available (too old?) — using Apify thumbnail")

            if carousel_urls:
                # GQL success: download ALL carousel images
                for i, url in enumerate(carousel_urls, 1):
                    filepath = os.path.join(post_dir, f"{shortcode}_{i:02d}.jpg")
                    if os.path.isfile(filepath) and os.path.getsize(filepath) > 1000:
                        print(f"  [SKIP] {shortcode}_{i:02d}.jpg exists")
                        dl_skip += 1
                    elif download_file(url, filepath,
                                       verify=not args.no_verify,
                                       insta_helper=insta_helper):
                        dl_ok += 1
                    else:
                        dl_fail += 1
            else:
                # Fallback: Apify thumbnail (first image only)
                if item["thumbnail_url"]:
                    filepath = os.path.join(post_dir, f"{shortcode}_01.jpg")
                    if os.path.isfile(filepath) and os.path.getsize(filepath) > 1000:
                        print(f"  [SKIP] {shortcode}_01.jpg exists")
                        dl_skip += 1
                    elif download_file(item["thumbnail_url"], filepath,
                                       verify=not args.no_verify,
                                       insta_helper=insta_helper):
                        dl_ok += 1
                    else:
                        dl_fail += 1
                else:
                    print(f"  [SKIP] No thumbnail URL for carousel")
                    dl_skip += 1

        # PHOTO
        elif post_type == "photo" and item["thumbnail_url"]:
            filepath = os.path.join(post_dir, f"{shortcode}_01.jpg")
            if os.path.isfile(filepath) and os.path.getsize(filepath) > 1000:
                print(f"  [SKIP] {shortcode}_01.jpg exists")
                dl_skip += 1
            elif download_file(item["thumbnail_url"], filepath,
                               verify=not args.no_verify,
                               insta_helper=insta_helper):
                dl_ok += 1
            else:
                dl_fail += 1

        else:
            print(f"  [SKIP] No downloadable media for type={post_type}")
            dl_skip += 1

    # ── Summary ──
    print("\n" + "=" * 55)
    print(" DOWNLOAD SUMMARY")
    print(f"  Total matched:     {len(filtered)}")
    for t in ("reel", "carousel", "photo", "unknown"):
        if stats.get(t, 0):
            print(f"  {t.capitalize():12s} {stats[t]}")
    if gql_hits or gql_misses:
        print(f"")
        print(f"  GQL carousel hits:  {gql_hits}")
        print(f"  GQL carousel misses: {gql_misses}")
    print(f"  Downloaded:        {dl_ok}")
    print(f"  Already existed:   {dl_skip}")
    print(f"  Failed:            {dl_fail}")
    print(f"  Output folder:     {os.path.abspath(args.output)}")
    print("=" * 55)

    return {"ok": dl_ok, "skip": dl_skip, "fail": dl_fail, "total": len(filtered)}


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = build_parser()
    args = parser.parse_args()

    # ── Validate input source ──
    use_api = bool(args.dataset)
    use_toon = bool(args.toon_file)

    if use_api and use_toon:
        print("ERROR: Use --dataset OR --toon-file, not both.")
        sys.exit(1)
    if not use_api and not use_toon:
        print("ERROR: Provide --dataset (with --api-token) OR --toon-file.")
        sys.exit(1)
    if use_api and not args.api_token:
        print("ERROR: --dataset requires --api-token.")
        sys.exit(1)
    if use_toon and not os.path.isfile(args.toon_file):
        print(f"ERROR: Toon file not found: {args.toon_file}")
        sys.exit(1)

    # ── Own-only / mentions-only validation ──
    if args.own_only and args.mentions_only:
        print("ERROR: Cannot use --own-only and --mentions-only together.")
        sys.exit(1)
    if (args.own_only or args.mentions_only) and not args.profile:
        print("ERROR: --own-only / --mentions-only requires --profile.")
        sys.exit(1)

    # ── Instagrapi init ──
    insta_helper = None
    if not args.no_instagrapi and HAS_INSTAGRAPI:
        insta_helper = InstagrapiHelper()
        print("✓ instagrapi available — carousel multi-image extraction enabled")
    elif args.no_instagrapi:
        print("  --no-instagrapi: using Apify thumbnails only for carousels")
    else:
        print("  instagrapi not installed. Install with: pip install instagrapi")
        print("  Carousel posts will use Apify thumbnails (first image only).\n")

    # ── Fetch data ──
    print("\nFetching data...")
    try:
        if use_api:
            print(f"  Mode: Apify API → dataset {args.dataset}")
            raw_items = fetch_from_api(args.dataset, args.api_token)
        else:
            print(f"  Mode: Toon file → {args.toon_file}")
            raw_items = fetch_from_toon(args.toon_file)
    except Exception as e:
        print(f"ERROR fetching data: {e}")
        sys.exit(1)

    if not raw_items:
        print("ERROR: No items found in data source.")
        sys.exit(1)

    print(f"  {len(raw_items)} raw items loaded\n")

    # ── Process ──
    result = process_items(raw_items, args, insta_helper)

    # ── Exit code ──
    if result["fail"] > 0:
        sys.exit(2)


if __name__ == "__main__":
    main()

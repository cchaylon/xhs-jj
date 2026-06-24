import re
import json
import asyncio
from typing import List, Optional, Dict
from urllib.parse import urlparse, parse_qs

from .auth import AuthManager, AuthMethod
from .models import Note, Author, NoteImage, NoteStats


class XhsCrawler:
    def __init__(
        self,
        auth_manager: Optional[AuthManager] = None,
        headless: bool = True,
        user_agent: Optional[str] = None,
    ):
        self.auth = auth_manager or AuthManager()
        self.headless = headless
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        from playwright.async_api import async_playwright

        print("[Crawler] Starting browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "user_agent": self.user_agent,
        }

        if self.auth.method == AuthMethod.COOKIE_FILE and self.auth.cookies:
            context_kwargs["storage_state"] = {
                "cookies": [
                    {k: v for k, v in c.items() if k in (
                        "name", "value", "domain", "path", "expires",
                        "httpOnly", "secure", "sameSite"
                    )}
                    for c in self.auth.cookies
                ],
                "origins": [],
            }

        self._context = await self._browser.new_context(**context_kwargs)
        self._page = await self._context.new_page()

        print("[Crawler] Browser started.")

    async def close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        print("[Crawler] Browser closed.")

    @staticmethod
    def extract_note_id(url: str) -> Optional[str]:
        match = re.search(r"/explore/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/discovery/item/([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        match = re.search(r"note_id=([a-zA-Z0-9]+)", url)
        if match:
            return match.group(1)
        return None

    async def fetch_note(self, url: str) -> Note:
        if not self._page:
            raise RuntimeError("Crawler not started. Call start() first or use 'async with'.")

        note_id = self.extract_note_id(url)
        if not note_id:
            raise ValueError(f"Cannot extract note ID from URL: {url}")

        print(f"[Crawler] Fetching note: {note_id}")

        await self._page.goto(url, wait_until="domcontentloaded")
        await self._wait_for_content()

        ssr_data = await self._extract_ssr_data()
        dom_data = await self._extract_dom_data()

        note = self._merge_data(note_id, url, ssr_data, dom_data)

        print(f"[Crawler] Note fetched: {note.title[:50]}...")
        return note

    async def _wait_for_content(self):
        try:
            await self._page.wait_for_function(
                "() => window.__INITIAL_STATE__ && window.__INITIAL_STATE__.note && "
                "Object.keys(window.__INITIAL_STATE__.note.noteDetailMap || {}).length > 0",
                timeout=15000,
            )
        except Exception:
            print("[Crawler] SSR data not found via wait_for, falling back to timeout...")
            await self._page.wait_for_timeout(5000)

    async def _extract_ssr_data(self) -> Dict:
        result = await self._page.evaluate("""
            () => {
                const state = window.__INITIAL_STATE__;
                if (!state || !state.note) return { found: false };

                const detailMap = state.note.noteDetailMap || {};
                const keys = Object.keys(detailMap);
                if (keys.length === 0) return { found: false };

                const firstKey = keys[0];
                const detail = detailMap[firstKey];
                const note = detail.note || detail;

                const imageList = note.imageList || [];
                const images = imageList.map(img => ({
                    urlDefault: img.urlDefault || img.url || img.urlPre || img.urlWatermark || '',
                    width: img.width || null,
                    height: img.height || null,
                    fileId: img.fileId || img.imageId || '',
                }));

                return {
                    found: true,
                    noteId: note.noteId || firstKey,
                    title: note.title || '',
                    desc: note.desc || '',
                    type: note.type || 'normal',
                    time: note.time || null,
                    lastUpdateTime: note.lastUpdateTime || null,
                    ipLocation: note.ipLocation || null,
                    user: note.user ? {
                        userId: note.user.userId || '',
                        nickname: note.user.nickname || '',
                        avatar: note.user.avatar || '',
                    } : null,
                    images: images,
                    imageCount: images.length,
                    tagList: (note.tagList || []).map(t => t.name || ''),
                    interactionInfo: note.interactionInfo ? {
                        likedCount: note.interactionInfo.likedCount ?? null,
                        collectedCount: note.interactionInfo.collectedCount ?? null,
                        commentCount: note.interactionInfo.commentCount ?? null,
                        shareCount: note.interactionInfo.shareCount ?? null,
                    } : null,
                };
            }
        """)
        return result

    async def _extract_dom_data(self) -> Dict:
        result = await self._page.evaluate("""
            () => {
                const data = {
                    title: '',
                    content: '',
                    tags: [],
                    images: [],
                    stats: {},
                    publishDate: '',
                    author: '',
                    authorAvatar: '',
                };

                const titleSelectors = [
                    '#detail-title',
                    '.note-content .title',
                    '[class*="note-content"] [class*="title"]',
                    'h1',
                ];
                for (const sel of titleSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim()) {
                        data.title = el.innerText.trim();
                        break;
                    }
                }

                const descSelectors = [
                    '#detail-desc',
                    '.note-content .desc',
                    '[class*="note-content"] [class*="desc"]',
                    '[class*="desc" i]',
                ];
                for (const sel of descSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim() && el.innerText.length > 20) {
                        data.content = el.innerText.trim();
                        break;
                    }
                }

                const tagEls = document.querySelectorAll('.topic, .hash-tag, [class*="tag"], [class*="topic"]');
                const seen = new Set();
                tagEls.forEach(el => {
                    const text = el.innerText.trim();
                    if (text.startsWith('#') && !seen.has(text)) {
                        seen.add(text);
                        data.tags.push(text.replace(/^#/, '').replace(/\\[话题\\]$/, ''));
                    }
                });

                const imgSelectors = [
                    '.note-swiper img',
                    '.swiper-slide img',
                    '.note-image-container img',
                    '.img-container img',
                    '[class*="note"] [class*="image"] img',
                    '.slides img',
                ];
                const imgUrls = new Set();
                for (const sel of imgSelectors) {
                    document.querySelectorAll(sel).forEach(img => {
                        const src = img.src || img.dataset.src;
                        if (src && src.includes('sns-webpic') && !imgUrls.has(src)) {
                            imgUrls.add(src);
                            data.images.push(src);
                        }
                    });
                }

                const likeEl = document.querySelector('.like-count, [class*="like"] [class*="count"], [class*="like-wrapper"] .count');
                const collectEl = document.querySelector('.collect-count, [class*="collect"] [class*="count"], [class*="collect-wrapper"] .count');
                const commentEl = document.querySelector('.comment-count, [class*="comment"] [class*="count"], [class*="comment-wrapper"] .count');

                if (likeEl) data.stats.likes = likeEl.innerText.trim();
                if (collectEl) data.stats.collects = collectEl.innerText.trim();
                if (commentEl) data.stats.comments = commentEl.innerText.trim();

                const dateEl = document.querySelector('.date, .publish-date, [class*="date"][class*="publish"]');
                if (dateEl) data.publishDate = dateEl.innerText.trim();

                const authorEl = document.querySelector('.author .name, .user-info .name, [class*="author"] [class*="name"], [class*="user-info"] [class*="name"]');
                if (authorEl) data.author = authorEl.innerText.trim();

                const avatarEl = document.querySelector('.author img, .user-info img, [class*="author"] img, [class*="user-avatar"] img');
                if (avatarEl && avatarEl.src) data.authorAvatar = avatarEl.src;

                return data;
            }
        """)
        return result

    def _merge_data(self, note_id: str, source_url: str, ssr_data: Dict, dom_data: Dict) -> Note:
        has_ssr = ssr_data.get("found", False)

        if has_ssr:
            title = ssr_data.get("title") or dom_data.get("title") or ""
            content = ssr_data.get("desc") or dom_data.get("content") or ""
            note_type = ssr_data.get("type", "normal")
            publish_time = ssr_data.get("time")
            publish_date = dom_data.get("publishDate") or self._ts_to_date(publish_time)

            author = None
            user_data = ssr_data.get("user")
            if user_data:
                author = Author(
                    user_id=user_data.get("userId", ""),
                    nickname=user_data.get("nickname") or dom_data.get("author") or "",
                    avatar=user_data.get("avatar") or dom_data.get("authorAvatar"),
                )
            elif dom_data.get("author"):
                author = Author(
                    user_id="",
                    nickname=dom_data["author"],
                    avatar=dom_data.get("authorAvatar"),
                )

            tags = ssr_data.get("tagList", [])
            if not tags:
                tags = dom_data.get("tags", [])

            images = []
            ssr_images = ssr_data.get("images", [])
            if ssr_images:
                for i, img in enumerate(ssr_images, 1):
                    images.append(NoteImage(
                        index=i,
                        url=img.get("urlDefault", ""),
                        width=img.get("width"),
                        height=img.get("height"),
                    ))
            else:
                for i, url in enumerate(dom_data.get("images", []), 1):
                    images.append(NoteImage(index=i, url=url))

            stats = None
            interaction = ssr_data.get("interactionInfo")
            dom_stats = dom_data.get("stats", {})
            if interaction or dom_stats:
                stats = NoteStats(
                    liked_count=dom_stats.get("likes") or (interaction.get("likedCount") if interaction else None),
                    collected_count=dom_stats.get("collects") or (interaction.get("collectedCount") if interaction else None),
                    comment_count=dom_stats.get("comments") or (interaction.get("commentCount") if interaction else None),
                    share_count=interaction.get("shareCount") if interaction else None,
                )

            return Note(
                note_id=note_id,
                title=title,
                content=content,
                note_type=note_type,
                publish_time=publish_time,
                publish_date=publish_date,
                author=author,
                tags=tags,
                images=images,
                stats=stats,
                ip_location=ssr_data.get("ipLocation"),
                source_url=source_url,
            )
        else:
            return Note(
                note_id=note_id,
                title=dom_data.get("title", ""),
                content=dom_data.get("content", ""),
                note_type="normal",
                publish_date=dom_data.get("publishDate") or "",
                author=Author(
                    user_id="",
                    nickname=dom_data.get("author", ""),
                    avatar=dom_data.get("authorAvatar"),
                ) if dom_data.get("author") else None,
                tags=dom_data.get("tags", []),
                images=[
                    NoteImage(index=i + 1, url=url)
                    for i, url in enumerate(dom_data.get("images", []))
                ],
                stats=NoteStats(
                    liked_count=dom_stats.get("likes"),
                    collected_count=dom_stats.get("collects"),
                    comment_count=dom_stats.get("comments"),
                ) if (dom_stats := dom_data.get("stats", {})) else None,
                source_url=source_url,
            )

    @staticmethod
    def _ts_to_date(ts: Optional[int]) -> str:
        if not ts:
            return ""
        try:
            from datetime import datetime
            dt = datetime.fromtimestamp(ts / 1000)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return ""

    async def fetch_notes_batch(self, urls: List[str], delay: float = 2.0) -> List[Note]:
        notes = []
        for i, url in enumerate(urls, 1):
            print(f"[Crawler] [{i}/{len(urls)}] Fetching...")
            try:
                note = await self.fetch_note(url)
                notes.append(note)
            except Exception as e:
                print(f"[Crawler] Failed to fetch {url}: {e}")
            if i < len(urls):
                await asyncio.sleep(delay)
        return notes

    async def fetch_user_notes(self, user_url: str, max_notes: int = 50) -> List[str]:
        if not self._page:
            raise RuntimeError("Crawler not started.")

        print(f"[Crawler] Fetching user notes from: {user_url}")
        await self._page.goto(user_url, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(3000)

        note_urls = []
        last_count = 0
        scroll_attempts = 0
        max_scrolls = 50

        while scroll_attempts < max_scrolls and len(note_urls) < max_notes:
            await self._page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await self._page.wait_for_timeout(2000)

            urls = await self._page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href*="/explore/"]');
                    const seen = new Set();
                    const result = [];
                    links.forEach(a => {
                        const href = a.href;
                        const match = href.match(/\\/explore\\/([a-zA-Z0-9]+)/);
                        if (match && !seen.has(match[1])) {
                            seen.add(match[1]);
                            result.push(href);
                        }
                    });
                    return result;
                }
            """)

            for url in urls:
                if url not in note_urls:
                    note_urls.append(url)

            if len(note_urls) == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = len(note_urls)

            print(f"[Crawler] Found {len(note_urls)} notes so far...")

        note_urls = note_urls[:max_notes]
        print(f"[Crawler] Total notes found: {len(note_urls)}")
        return note_urls

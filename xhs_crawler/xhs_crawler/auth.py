import re
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from enum import Enum


class AuthMethod(str, Enum):
    BROWSER_LOGIN = "browser"
    COOKIE_FILE = "cookie"


class CookieParser:
    @staticmethod
    def parse_netscape_cookie_file(file_path: str) -> List[Dict]:
        cookies = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 7:
                    continue
                domain, flag, path, secure, expires, name, value = parts[:7]
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": path,
                    "expires": int(expires) if expires.isdigit() else -1,
                    "httpOnly": flag.upper() == "TRUE",
                    "secure": secure.upper() == "TRUE",
                })
        return cookies

    @staticmethod
    def parse_json_cookie_file(file_path: str) -> List[Dict]:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "cookies" in data:
            return data["cookies"]
        return []

    @staticmethod
    def parse_cookie_string(cookie_str: str) -> List[Dict]:
        cookies = []
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        return cookies

    @classmethod
    def auto_parse(cls, file_path: str) -> List[Dict]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Cookie file not found: {file_path}")

        content = path.read_text(encoding="utf-8").strip()

        if content.startswith("[") or content.startswith("{"):
            try:
                return cls.parse_json_cookie_file(file_path)
            except json.JSONDecodeError:
                pass

        if "\t" in content and ("# Netscape" in content or any(
            line.strip().count("\t") >= 6
            for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )):
            return cls.parse_netscape_cookie_file(file_path)

        if "=" in content and ";" in content:
            return cls.parse_cookie_string(content)

        raise ValueError(f"Unsupported cookie file format: {file_path}")


class AuthManager:
    def __init__(self, method: AuthMethod = AuthMethod.BROWSER_LOGIN, cookie_file: Optional[str] = None):
        self.method = method
        self.cookie_file = cookie_file
        self._cookies: List[Dict] = []
        self._storage_state: Optional[Dict] = None

    @property
    def cookies(self) -> List[Dict]:
        return self._cookies

    def load_from_cookie_file(self, file_path: Optional[str] = None) -> List[Dict]:
        path = file_path or self.cookie_file
        if not path:
            raise ValueError("Cookie file path is required")
        self._cookies = CookieParser.auto_parse(path)
        print(f"[Auth] Loaded {len(self._cookies)} cookies from {path}")
        return self._cookies

    async def login_via_browser(self, headless: bool = False, timeout: int = 300) -> List[Dict]:
        from playwright.async_api import async_playwright

        print("[Auth] Starting browser for login...")
        print("[Auth] Please scan the QR code or login manually in the browser window.")
        print(f"[Auth] Will wait up to {timeout} seconds for login...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            await page.goto("https://www.xiaohongshu.com/explore")
            await page.wait_for_timeout(2000)

            start_time = time.time()
            logged_in = False

            while time.time() - start_time < timeout:
                current_url = page.url
                cookies = await context.cookies()
                has_session = any(c["name"] in ("web_session", "a1", "xsec_token") for c in cookies)

                if has_session and "login" not in current_url:
                    logged_in = True
                    print("[Auth] Login detected! Waiting for page to stabilize...")
                    await page.wait_for_timeout(3000)
                    break

                await page.wait_for_timeout(2000)

            if not logged_in:
                print("[Auth] Warning: Login not confirmed within timeout. Saving cookies anyway.")

            self._cookies = await context.cookies()
            self._storage_state = await context.storage_state()

            print(f"[Auth] Login complete. Saved {len(self._cookies)} cookies.")

            await browser.close()

        return self._cookies

    def save_cookies(self, output_path: str) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._cookies, f, indent=2, ensure_ascii=False)

        print(f"[Auth] Cookies saved to {output_path}")

    def save_storage_state(self, output_path: str) -> None:
        if not self._storage_state:
            raise ValueError("No storage state available. Login first.")
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._storage_state, f, indent=2, ensure_ascii=False)

        print(f"[Auth] Storage state saved to {output_path}")

    async def authenticate(self, headless: bool = False) -> List[Dict]:
        if self.method == AuthMethod.COOKIE_FILE:
            return self.load_from_cookie_file()
        elif self.method == AuthMethod.BROWSER_LOGIN:
            return await self.login_via_browser(headless=headless)
        else:
            raise ValueError(f"Unknown auth method: {self.method}")

    def get_cookie_value(self, name: str) -> Optional[str]:
        for cookie in self._cookies:
            if cookie.get("name") == name:
                return cookie.get("value")
        return None

#!/usr/bin/env python3
"""
小红书笔记爬取工具 CLI

支持两种认证方式：
1. 浏览器登录扫码 - 交互式登录，适合首次使用
2. Cookie 文件导入 - 直接使用已有 cookie，适合自动化

用法示例：
  # 方式1：浏览器扫码登录爬取单篇笔记
  python cli.py note "https://www.xiaohongshu.com/explore/xxx" --auth browser

  # 方式2：使用 cookie 文件爬取
  python cli.py note "https://www.xiaohongshu.com/explore/xxx" --auth cookie --cookie-file cookies.txt

  # 登录并保存 cookie 供后续使用
  python cli.py login --save-cookie cookies.json

  # 批量爬取笔记
  python cli.py batch urls.txt --auth cookie --cookie-file cookies.json

  # 爬取用户主页所有笔记
  python cli.py user "https://www.xiaohongshu.com/user/profile/xxx" --auth browser
"""

import asyncio
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from xhs_crawler import XhsCrawler, AuthManager, AuthMethod
from xhs_crawler.utils import save_note_json, save_notes_batch, print_note_summary


def build_auth_manager(args) -> AuthManager:
    if args.auth == "browser":
        return AuthManager(method=AuthMethod.BROWSER_LOGIN)
    elif args.auth == "cookie":
        if not args.cookie_file:
            raise ValueError("--cookie-file is required when using cookie auth")
        return AuthManager(method=AuthMethod.COOKIE_FILE, cookie_file=args.cookie_file)
    else:
        raise ValueError(f"Unknown auth method: {args.auth}")


async def cmd_login(args):
    auth = AuthManager(method=AuthMethod.BROWSER_LOGIN)
    await auth.login_via_browser(headless=args.headless, timeout=args.timeout)

    if args.save_cookie:
        auth.save_cookies(args.save_cookie)
    if args.save_state:
        auth.save_storage_state(args.save_state)

    print("\n✅ 登录完成！")


async def cmd_note(args):
    auth = build_auth_manager(args)

    if args.auth == "cookie":
        auth.load_from_cookie_file()
    else:
        await auth.login_via_browser(headless=args.headless, timeout=args.timeout)
        if args.save_cookie:
            auth.save_cookies(args.save_cookie)

    async with XhsCrawler(auth_manager=auth, headless=args.headless) as crawler:
        note = await crawler.fetch_note(args.url)
        print_note_summary(note)

        if args.output:
            path = save_note_json(note, args.output)
            print(f"\n💾 结果已保存到: {path}")


async def cmd_batch(args):
    auth = build_auth_manager(args)

    if args.auth == "cookie":
        auth.load_from_cookie_file()
    else:
        await auth.login_via_browser(headless=args.headless, timeout=args.timeout)

    with open(args.input_file, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"📋 共 {len(urls)} 个笔记链接待爬取")

    async with XhsCrawler(auth_manager=auth, headless=args.headless) as crawler:
        notes = await crawler.fetch_notes_batch(urls, delay=args.delay)

    print(f"\n✅ 成功爬取 {len(notes)}/{len(urls)} 篇笔记")

    output_dir = args.output or "output"
    path = save_notes_batch(notes, output_dir)
    print(f"💾 批量结果已保存到: {path}")

    for i, note in enumerate(notes, 1):
        print(f"  [{i}] {note.note_id} - {note.title[:40]}")


async def cmd_user(args):
    auth = build_auth_manager(args)

    if args.auth == "cookie":
        auth.load_from_cookie_file()
    else:
        await auth.login_via_browser(headless=args.headless, timeout=args.timeout)

    async with XhsCrawler(auth_manager=auth, headless=args.headless) as crawler:
        note_urls = await crawler.fetch_user_notes(args.url, max_notes=args.max_notes)

        if args.list_only:
            print(f"\n📋 找到 {len(note_urls)} 篇笔记：")
            for i, url in enumerate(note_urls, 1):
                print(f"  [{i}] {url}")
            return

        notes = await crawler.fetch_notes_batch(note_urls, delay=args.delay)

    print(f"\n✅ 成功爬取 {len(notes)}/{len(note_urls)} 篇笔记")

    output_dir = args.output or "output"
    path = save_notes_batch(notes, output_dir)
    print(f"💾 结果已保存到: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="小红书笔记爬取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式（不显示浏览器窗口）",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    login_parser = subparsers.add_parser("login", help="登录并保存凭证")
    login_parser.add_argument("--save-cookie", help="保存 cookie 到指定文件")
    login_parser.add_argument("--save-state", help="保存 storage state 到指定文件")
    login_parser.add_argument("--timeout", type=int, default=300, help="登录超时时间（秒）")

    note_parser = subparsers.add_parser("note", help="爬取单篇笔记")
    note_parser.add_argument("url", help="笔记 URL")
    note_parser.add_argument(
        "--auth", choices=["browser", "cookie"], default="browser",
        help="认证方式（默认: browser）",
    )
    note_parser.add_argument("--cookie-file", help="Cookie 文件路径（cookie 认证时必需）")
    note_parser.add_argument("--output", "-o", help="输出目录（默认: output）")
    note_parser.add_argument("--save-cookie", help="登录后保存 cookie 到指定文件")
    note_parser.add_argument("--timeout", type=int, default=300, help="登录超时时间（秒）")

    batch_parser = subparsers.add_parser("batch", help="批量爬取笔记")
    batch_parser.add_argument("input_file", help="包含笔记 URL 的文件（每行一个）")
    batch_parser.add_argument(
        "--auth", choices=["browser", "cookie"], default="cookie",
        help="认证方式（默认: cookie）",
    )
    batch_parser.add_argument("--cookie-file", help="Cookie 文件路径")
    batch_parser.add_argument("--output", "-o", help="输出目录（默认: output）")
    batch_parser.add_argument("--delay", type=float, default=2.0, help="请求间隔（秒，默认: 2）")

    user_parser = subparsers.add_parser("user", help="爬取用户主页所有笔记")
    user_parser.add_argument("url", help="用户主页 URL")
    user_parser.add_argument(
        "--auth", choices=["browser", "cookie"], default="browser",
        help="认证方式（默认: browser）",
    )
    user_parser.add_argument("--cookie-file", help="Cookie 文件路径")
    user_parser.add_argument("--max-notes", type=int, default=50, help="最大爬取数量（默认: 50）")
    user_parser.add_argument("--output", "-o", help="输出目录（默认: output）")
    user_parser.add_argument("--delay", type=float, default=2.0, help="请求间隔（秒，默认: 2）")
    user_parser.add_argument("--list-only", action="store_true", help="仅列出笔记 URL，不爬取内容")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "login": cmd_login,
        "note": cmd_note,
        "batch": cmd_batch,
        "user": cmd_user,
    }

    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()

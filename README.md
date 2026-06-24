# xhs-jj

小红书笔记爬取工具，基于 Playwright 浏览器自动化。

## 功能特性

- 爬取单篇笔记详情（标题、正文、图片、标签、互动数据等）
- 批量爬取多篇笔记
- 爬取用户主页全部笔记
- 支持两种认证方式：浏览器扫码登录 / Cookie 文件导入
- 数据优先从页面 SSR 数据提取，DOM 解析作为补充

## 项目结构

```
xhs-jj/
├── __init__.py      # 包入口，导出核心类
├── auth.py          # 认证管理（Cookie 解析 + 浏览器登录）
├── crawler.py       # 笔记爬取器（Playwright）
├── models.py        # 数据模型（Note、Author、NoteImage、NoteStats）
├── utils.py         # 工具函数（保存/打印）
├── cli.py           # CLI 入口脚本
├── requirements.txt # 依赖清单
└── doc/
    └── SOP.md       # 详细操作手册
```

## 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

## 快速开始

### 1. 扫码登录并保存 Cookie

```bash
python cli.py login --save-cookie cookies.json
```

### 2. 爬取单篇笔记

```bash
python cli.py note "https://www.xiaohongshu.com/explore/笔记ID" \
  --auth cookie --cookie-file cookies.json --output output
```

### 3. 批量爬取

```bash
python cli.py batch urls.txt --auth cookie --cookie-file cookies.json --output output
```

### 4. 爬取用户主页笔记

```bash
python cli.py user "https://www.xiaohongshu.com/user/profile/用户ID" \
  --auth cookie --cookie-file cookies.json --max-notes 50
```

### 5. 使用配置文件启动（推荐）

编辑 `crawler_config.txt`：

```
note_url:https://www.xiaohongshu.com/explore/笔记ID1,https://www.xiaohongshu.com/explore/笔记ID2
cookie:your_cookie_here
```

直接运行：

```bash
python cli.py run
```

## 认证方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| `browser` | 浏览器扫码登录 | 首次使用，无现成 Cookie |
| `cookie` | 导入 Cookie 文件 | 自动化批量爬取 |

支持的 Cookie 格式：Netscape (.txt)、JSON (.json)、Cookie 字符串 (.txt)

## 输出数据

每篇笔记输出 JSON 文件，包含字段：

- `note_id` - 笔记 ID
- `title` - 标题
- `content` - 正文内容
- `note_type` - 笔记类型
- `publish_time` / `publish_date` - 发布时间
- `author` - 作者信息（user_id、nickname、avatar）
- `tags` - 标签列表
- `images` - 图片列表（index、url、width、height）
- `stats` - 互动数据（点赞、收藏、评论、分享）
- `ip_location` - IP 属地
- `source_url` - 原始链接

## 命令参考

```bash
# 登录
python cli.py login [--save-cookie FILE] [--save-state FILE] [--timeout SEC] [--headless]

# 使用配置文件启动（推荐）
python cli.py run [--config FILE] [--output DIR] [--delay SEC] [--headless]

# 单篇笔记
python cli.py note URL [--auth browser|cookie] [--cookie-file FILE] [--output DIR] [--save-cookie FILE] [--headless]

# 批量爬取
python cli.py batch INPUT_FILE [--auth browser|cookie] [--cookie-file FILE] [--output DIR] [--delay SEC] [--headless]

# 用户主页
python cli.py user URL [--auth browser|cookie] [--cookie-file FILE] [--max-notes N] [--output DIR] [--delay SEC] [--list-only] [--headless]
```

## 技术栈

- **Playwright** - 浏览器自动化
- **Python 3.8+** - 运行环境

## 注意事项

- 本工具仅供学习研究使用
- 请遵守小红书《用户协议》和《robots.txt》
- 合理控制爬取频率，避免账号被限流

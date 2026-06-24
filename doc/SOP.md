# 小红书笔记爬取工具 - SOP 标准操作流程

## 目录

1. [项目概述](#1-项目概述)
2. [环境准备](#2-环境准备)
3. [认证方式说明](#3-认证方式说明)
4. [操作流程](#4-操作流程)
5. [常见问题](#5-常见问题)
6. [注意事项](#6-注意事项)

---

## 1. 项目概述

### 1.1 功能

- 爬取小红书单篇笔记详情（标题、正文、图片、标签、互动数据等）
- 批量爬取多篇笔记
- 爬取用户主页全部笔记
- 支持两种认证方式：浏览器扫码登录 / Cookie 文件导入

### 1.2 技术架构

```
xhs_crawler/
├── xhs_crawler/
│   ├── __init__.py      # 包入口
│   ├── auth.py          # 认证管理（浏览器登录 + Cookie解析）
│   ├── crawler.py       # 笔记爬取器（Playwright）
│   ├── models.py        # 数据模型（Note/Author/NoteImage等）
│   └── utils.py         # 工具函数（保存/打印）
├── cli.py               # CLI 入口脚本
├── requirements.txt     # 依赖清单
└── SOP.md               # 本文档
```

### 1.3 核心原理

- **数据提取方式**：优先从页面 SSR 数据 `window.__INITIAL_STATE__` 提取（结构化、完整），DOM 解析作为补充
- **浏览器引擎**：Playwright（Chromium），模拟真实浏览器行为
- **反爬策略**：随机延迟、真实 User-Agent、完整浏览器环境

---

## 2. 环境准备

### 2.1 系统要求

- Python 3.8+
- 支持 Windows / macOS / Linux
- 足够的磁盘空间（Chromium 浏览器约 300MB）

### 2.2 安装步骤

#### 步骤 1：安装 Python 依赖

```bash
cd xhs_crawler
pip install -r requirements.txt
```

#### 步骤 2：安装 Playwright 浏览器

```bash
playwright install chromium
```

或者使用系统依赖：

```bash
playwright install-deps chromium
```

#### 步骤 3：验证安装

```bash
python cli.py --help
```

如果正常显示帮助信息，说明安装成功。

---

## 3. 认证方式说明

### 3.1 方式一：浏览器扫码登录（推荐首次使用）

**适用场景**：
- 首次使用，没有现成的 Cookie
- 需要完整的登录态
- 交互式操作

**操作流程**：
1. 工具启动 Chromium 浏览器
2. 自动打开小红书探索页
3. 用户使用小红书 App 扫描二维码登录
4. 工具检测登录状态并保存 Cookie
5. 后续爬取自动使用登录态

**优点**：
- 操作简单，只需扫码
- 登录态完整，功能不受限
- 可保存 Cookie 供后续使用

**缺点**：
- 需要人工干预扫码
- 不适合纯自动化场景

### 3.2 方式二：Cookie 文件导入（适合自动化）

**适用场景**：
- 已有可复用的 Cookie
- 自动化批量爬取
- CI/CD 环境

**支持的 Cookie 文件格式**：

| 格式 | 说明 | 后缀 |
|------|------|------|
| Netscape | 经典 cookie 格式（GetCookie.txt 导出） | .txt |
| JSON | Playwright / 浏览器导出的 JSON 格式 | .json |
| Cookie 字符串 | `name1=value1; name2=value2` 格式 | .txt |

**获取 Cookie 的方法**：
1. 从浏览器开发者工具 → Application → Cookies 复制
2. 使用浏览器扩展（如 Get cookies.txt LOCALLY）导出
3. 使用本工具的 `login` 命令生成

**优点**：
- 无需人工干预，完全自动化
- 速度快，启动即爬取
- 适合批量任务

**缺点**：
- Cookie 有有效期，过期需要更新
- 需要提前获取有效的 Cookie

---

## 4. 操作流程

### 4.1 快速开始

#### 场景 A：首次使用，扫码登录爬取单篇笔记

```bash
# 1. 扫码登录并保存 cookie（推荐先做这步）
python cli.py login --save-cookie cookies.json

# 2. 爬取笔记
python cli.py note "https://www.xiaohongshu.com/explore/笔记ID" \
  --auth cookie \
  --cookie-file cookies.json \
  --output output
```

#### 场景 B：已有 Cookie，直接爬取

```bash
python cli.py note "笔记链接" --auth cookie --cookie-file cookies.txt
```

#### 场景 C：批量爬取

```bash
# 准备 urls.txt，每行一个笔记链接
python cli.py batch urls.txt --auth cookie --cookie-file cookies.json
```

#### 场景 D：爬取用户全部笔记

```bash
python cli.py user "https://www.xiaohongshu.com/user/profile/用户ID" \
  --auth cookie \
  --cookie-file cookies.json \
  --max-notes 100
```

### 4.2 详细操作步骤

#### 4.2.1 登录并保存凭证

```bash
python cli.py login \
  --save-cookie cookies.json \
  --save-state state.json \
  --timeout 300
```

**操作步骤**：
1. 执行命令后，浏览器窗口会自动打开
2. 页面显示小红书登录二维码
3. 打开小红书 App → 我 → 扫一扫
4. 扫描二维码并在手机上确认登录
5. 工具自动检测登录状态
6. 登录成功后，Cookie 会自动保存到指定文件

**输出示例**：
```
[Auth] Starting browser for login...
[Auth] Please scan the QR code or login manually in the browser window.
[Auth] Will wait up to 300 seconds for login...
[Auth] Login detected! Waiting for page to stabilize...
[Auth] Login complete. Saved 42 cookies.
[Auth] Cookies saved to cookies.json
[Auth] Storage state saved to state.json

✅ 登录完成！
```

#### 4.2.2 爬取单篇笔记

```bash
python cli.py note "https://www.xiaohongshu.com/explore/6475426b0000000013031778?xsec_token=xxx" \
  --auth cookie \
  --cookie-file cookies.json \
  --output output
```

**输出示例**：
```
[Crawler] Starting browser...
[Crawler] Browser started.
[Crawler] Fetching note: 6475426b0000000013031778
[Crawler] Note fetched: 半夜睡醒都得给自己两巴掌。。。的后续

============================================================
📝 笔记详情
============================================================
  笔记ID: 6475426b0000000013031778
  标题: 半夜睡醒都得给自己两巴掌。。。的后续
  作者: 羔仔阳🌟 (ID: 635dd59e000000001901d29b)
  发布时间: 2023-05-30
  类型: normal
  标签: 大学生, 奇葩, 校园表白墙, 表白墙, 搞笑, 沙雕
  图片数: 3
  点赞: 3.6万
  收藏: 3057
  评论: 4728
  链接: https://...
============================================================

💾 结果已保存到: output/note_6475426b0000000013031778.json
[Crawler] Browser closed.
```

#### 4.2.3 批量爬取

**准备 URL 文件**（`urls.txt`）：
```
# 笔记链接列表，每行一个
# 以 # 开头的行会被忽略
https://www.xiaohongshu.com/explore/笔记ID1
https://www.xiaohongshu.com/explore/笔记ID2
https://www.xiaohongshu.com/explore/笔记ID3
```

**执行批量爬取**：
```bash
python cli.py batch urls.txt \
  --auth cookie \
  --cookie-file cookies.json \
  --output output \
  --delay 3
```

#### 4.2.4 爬取用户主页笔记

```bash
python cli.py user "https://www.xiaohongshu.com/user/profile/用户ID" \
  --auth cookie \
  --cookie-file cookies.json \
  --max-notes 50 \
  --delay 2
```

**仅列出笔记 URL，不爬取内容**：
```bash
python cli.py user "用户主页链接" \
  --auth cookie \
  --cookie-file cookies.json \
  --list-only
```

### 4.3 输出数据结构

输出的 JSON 文件包含以下字段：

```json
{
  "note_id": "笔记ID",
  "title": "笔记标题",
  "content": "笔记正文内容",
  "note_type": "normal",
  "publish_time": 1685406315000,
  "publish_date": "2023-05-30",
  "author": {
    "user_id": "用户ID",
    "nickname": "昵称",
    "avatar": "头像URL"
  },
  "tags": ["标签1", "标签2"],
  "images": [
    {
      "index": 1,
      "url": "图片URL",
      "width": 1080,
      "height": 1440
    }
  ],
  "stats": {
    "liked_count": "3.6万",
    "collected_count": "3057",
    "comment_count": "4728",
    "share_count": null
  },
  "ip_location": "IP属地",
  "source_url": "原始链接"
}
```

---

## 5. 常见问题

### 5.1 登录相关

**Q: 扫码后一直没反应？**
A: 确认手机上已点击"确认登录"，可能有几秒延迟。如果超过 30 秒没反应，刷新页面重试。

**Q: Cookie 过期了怎么办？**
A: 重新运行 `python cli.py login --save-cookie cookies.json` 扫码更新。

**Q: Cookie 文件格式不支持？**
A: 支持 Netscape、JSON、Cookie 字符串三种格式。如果都不行，可以先用 `login` 命令生成标准 JSON 格式。

### 5.2 爬取相关

**Q: 爬取失败，提示需要登录？**
A: 检查 Cookie 是否有效，可能 Cookie 已过期，重新登录获取新 Cookie。

**Q: 笔记内容不完整？**
A: 
1. 确认网络连接正常
2. 增加页面等待时间
3. 检查是否触发了小红书的风控

**Q: 图片 URL 打不开？**
A: 小红书图片有防盗链和时效限制，建议爬取后立即下载保存。

### 5.3 运行环境

**Q: Linux 服务器上运行报错？**
A: 需要安装 Chromium 依赖：
```bash
playwright install-deps chromium
```

**Q: 能不能在无 GUI 的服务器上运行？**
A: 可以，使用 `--headless` 参数启用无头模式。但浏览器登录（扫码）需要可视化环境，建议先在本地登录获取 Cookie，再在服务器上使用 Cookie 认证。

---

## 6. 注意事项

### 6.1 合规提醒

- 本工具仅供学习和研究使用
- 请遵守小红书的《用户协议》和《robots.txt》
- 请勿用于商业用途
- 爬取数据请尊重原作者知识产权

### 6.2 反爬建议

| 建议 | 说明 |
|------|------|
| 控制频率 | 单篇笔记间隔建议 2-5 秒，不要过快 |
| 数量限制 | 单次爬取不要超过 100 篇，分批进行 |
| 使用代理 | 大量爬取建议使用代理 IP 池 |
| 时段分散 | 避免在短时间内集中爬取 |
| 账号保护 | 不要使用重要账号爬取，建议用小号 |

### 6.3 风险提示

- 频繁爬取可能导致账号被限流或封禁
- IP 可能被加入黑名单
- 小红书的页面结构和接口可能随时变化，工具可能失效

### 6.4 更新维护

如遇页面结构变化导致爬取失败，需更新以下内容：
1. `crawler.py` 中的 CSS 选择器
2. `_extract_ssr_data` 中的数据解析逻辑
3. `_extract_dom_data` 中的 DOM 提取逻辑

---

## 附录：完整命令参考

```bash
# 登录
python cli.py login [--save-cookie FILE] [--save-state FILE] [--timeout SEC]

# 单篇笔记
python cli.py note URL [--auth browser|cookie] [--cookie-file FILE] 
                      [--output DIR] [--save-cookie FILE] [--headless]

# 批量爬取
python cli.py batch INPUT_FILE [--auth browser|cookie] [--cookie-file FILE]
                              [--output DIR] [--delay SEC] [--headless]

# 用户主页
python cli.py user URL [--auth browser|cookie] [--cookie-file FILE]
                       [--max-notes N] [--output DIR] [--delay SEC]
                       [--list-only] [--headless]
```

---

**文档版本**：v0.1.0  
**最后更新**：2026-06-24

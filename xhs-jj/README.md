# 小红书笔记爬取工具

基于 Playwright 的小红书笔记爬取工具，支持两种认证方式。

## 功能特性

- 📝 爬取单篇笔记详情（标题、正文、图片、标签、互动数据）
- 📚 批量爬取多篇笔记
- 👤 爬取用户主页全部笔记
- 🔐 支持两种认证方式：
  - **浏览器扫码登录** - 交互式，适合首次使用
  - **Cookie 文件导入** - 自动化，适合批量爬取
- 💾 数据导出为 JSON 格式
- 🎯 双重提取策略：SSR 数据 + DOM 解析，确保数据完整

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 登录获取 Cookie（首次使用）

```bash
python cli.py login --save-cookie cookies.json
```

扫码登录后，Cookie 会保存到 `cookies.json`。

### 3. 爬取笔记

```bash
python cli.py note "https://www.xiaohongshu.com/explore/笔记ID" \
  --auth cookie \
  --cookie-file cookies.json
```

## 命令一览

```bash
# 登录并保存凭证
python cli.py login --save-cookie cookies.json

# 爬取单篇笔记
python cli.py note <笔记URL> --auth cookie --cookie-file cookies.json

# 批量爬取
python cli.py batch urls.txt --auth cookie --cookie-file cookies.json

# 爬取用户主页全部笔记
python cli.py user <用户主页URL> --auth cookie --cookie-file cookies.json
```

## 项目结构

```
xhs_crawler/
├── xhs_crawler/
│   ├── __init__.py      # 包入口
│   ├── auth.py          # 认证模块
│   ├── crawler.py       # 笔记爬取器
│   ├── models.py        # 数据模型
│   └── utils.py         # 工具函数
├── doc/
│   └── SOP.md           # 标准操作流程
├── cli.py               # CLI 入口
├── requirements.txt     # 依赖
└── README.md            # 本文件
```

## 详细文档

更多使用说明请参考 [SOP.md](./doc/SOP.md)。

## 免责声明

本工具仅供学习和研究使用，请遵守小红书服务条款，勿用于商业用途。

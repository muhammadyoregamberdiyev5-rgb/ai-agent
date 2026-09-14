---
name: binance-square-scraper
description: 用 browser-harness 抓取币安广场 (Binance Square) 热点话题、高讨论帖子、热搜币种，并生成带可点击跳转链接的 HTML 报告。
tags: [binance, crypto, scraping, browser-harness]
---

# Binance Square 热点抓取

## 触发条件

用户要求抓取币安广场热点、热门帖子、讨论度排名等。

## 关键发现（字段测试得出）

- **Binance Square 是 React SPA**，`js()` helper 直接返回 `None`，必须用 `cdp("Runtime.evaluate", expression="...", returnByValue=True)` 提取 DOM 数据。
- `wait_for_load()` 会**无限挂起**，改用 `goto(url)` + `time.sleep(8)` 等待渲染。
- 用 `new_tab(url)` 后需再次调用 `time.sleep(8)`，不能依赖 load 事件。

## URL 结构

```
帖子原文：  https://www.binance.com/zh-CN/square/post/{postId}
话题页：    https://www.binance.com/zh-CN/square/hashtag/{encodedTopic}
用户主页：  https://www.binance.com/zh-CN/square/profile/{handle}
恐惧贪婪：  https://www.binance.com/zh-CN/square/fear-and-greed-index
热门话题：  https://www.binance.com/zh-CN/square/trends
交易对：    https://www.binance.com/zh-CN/trade/{COIN}_USDT
合约：      https://www.binance.com/zh-CN/futures/{COIN}USDT
```

## 抓取步骤

```python
# Step 1: 导航并等待渲染
new_tab("https://www.binance.com/zh-CN/square")
time.sleep(8)

# Step 2: 用 cdp Runtime.evaluate 提取文本
text = cdp("Runtime.evaluate",
    expression="document.body.innerText.substring(0, 5000)",
    returnByValue=True)
content = text['result']['value']

# Step 3: 提取所有链接（含帖子/话题/交易对）
links_raw = cdp("Runtime.evaluate", expression="""
(function() {
    const links = [];
    document.querySelectorAll('a').forEach(a => {
        if (a.href && a.href.length > 10) {
            links.push({href: a.href, text: (a.innerText || '').trim().substring(0, 80)});
        }
    });
    return JSON.stringify(links.slice(0, 60));
})()
""", returnByValue=True)
links = json.loads(links_raw['result']['value'])

# Step 4: 滚动获取更多帖子
cdp("Runtime.evaluate", expression="window.scrollBy(0, 2000)", returnByValue=True)
time.sleep(3)
# 再次抓取链接...
```

## 数据分类

从 `innerText` 中可提取：
- **热门话题**：带 `次浏览` 和 `人讨论中` 的段落
- **帖子正文**：作者名 + 时间 + 内容 + 互动数
- **热搜币种**：`热度上升` 标记 + 价格 + 涨跌幅
- **恐惧贪婪指数**：数字 + 状态词（中性/恐惧/贪婪）

从链接列表中可提取：
- `/square/post/{id}` → 帖子原文 URL
- `/square/hashtag/{encoded}` → 话题页 URL
- `/trade/{COIN}_USDT` → 交易页 URL

## 输出要求（用户偏好）

输出 HTML 报告，保存到 `~/Documents/Hermes/`，要求：
- **所有内容必须可点击跳转**：帖子 → 原帖、话题 → 话题页、币种 → 交易页
- 卡片悬停有金色边框 + 位移动画（符合币安风格 #f0b90b）
- 暗色主题（背景 #0b0e11）
- 帖子卡片包含：作者、时间、正文摘要（4行截断）、涨跌标签、"查看原帖 →" 按钮
- 话题卡片包含：排名徽章、浏览量、讨论人数
- 底部注明数据来源和免责声明

## 坑

- `js()` helper 对 Binance Square **无效**，永远返回 None。必须走 `cdp()` 路径。
- 话题链接中中文会被 URL encode，要用 `encodeURIComponent` 或直接从链接列表里取。
- 页面初次加载只显示 ~4 条帖子，需滚动后才能加载更多。
- **macOS 系统 SOCKS 代理（YOUR_PROXY_HOST:PORT）会导致 browser-harness daemon 连接 ws://localhost:9222 报错**：`connecting through a SOCKS proxy requires python-socks`。修复：在 harness 的 uv venv 中安装 python-socks。
- **Chrome 必须用 `--headless=new` + `/tmp` 临时目录启动**：直接用真实 user-data-dir 会报 "requires non-default data directory"。
- **Chrome 每次重启后 WS URL 中的 browser UUID 会变**，必须重新获取并重新设置 `BU_CDP_WS` 环境变量。
- `/tmp/chromedebug` 路径不在 browser-harness PROFILES 自动发现列表中，必须手动设置 `BU_CDP_WS` 环境变量或写入 `DevToolsActivePort` 文件。
- **最简启动方式**：`nohup chrome --headless=new --remote-debugging-port=9222 --user-data-dir=/tmp/chromedebug ... &` → sleep 5 → `WS=$(curl json/version | parse wsUrl)` → `BU_CDP_WS="$WS" browser-harness < script.py`

---
name: xiaohongshu
description: 小红书全自动发布技能。一键完成手机号验证码登录、内容策略、图片获取、Playwright 自动发帖。支持 AI 文案、网页图片/截图、AI 生图、视频选题预案。
---

# 小红书全自动发布技能

## 快速开始

```bash
# 一键发布（推荐：Playwright，可见 Chrome + 持久化 profile）
python xhs_auto.py --topic "天气" --images /path/to/image.png --auto-publish --browser-method playwright

# 指定主题并发布
python xhs_auto.py --topic "上海迪士尼攻略" --auto-publish

# 从网页截取图片并发布
python xhs_auto.py --topic "美景分享" --url "https://example.com" --capture-images --auto-publish

# 仅生成内容不发布
python xhs_auto.py --topic "美食" --dry-run

# 检查登录状态
python xhs_auto.py --action check-login

# 生成选题/素材策略（图文或视频都可用）
python xhs_auto.py --action plan --topic "上海天气" --city "上海" --format note --image-method auto

# 趋势采集：支持通用领域，不限城市
python xhs_auto.py --action trends --domain "ai" --keywords "AI安全" "智能体" "模型评测"

# 标题候选生成
python xhs_auto.py --action titles --domain "ai" --topic "语音AI" --content-file copy.md

# 发布前自动优化标题
python xhs_auto.py --title "语音AI开始办事了" --content-file copy.md --images cover.png --auto-publish --browser-method playwright --domain ai --optimize-title

# 真人刷站内搜索，采集页面文本，再生成选题候选
python xhs_auto.py --action trends --domain "travel" --live-xhs --keywords "小众旅行" "高铁直达" "错峰出行"

# 未登录时，Playwright 会提示输入手机号，点击发送验证码后等待输入短信验证码
python xhs_auto.py --topic "上海天气" --images /path/to/image.png --auto-publish --browser-method playwright --login-phone <PHONE_NUMBER>

# 只执行 Playwright 手机号验证码登录
python xhs_auto.py --action login --browser-method playwright --login-phone <PHONE_NUMBER>
```

## 核心功能

| 功能 | 说明 |
|------|------|
| 自动登录 | Playwright 手机号短信登录 |
| AI 文案生成 | 根据主题自动生成标题、正文、标签 |
| 图片获取 | AI 生图 / 网页截取 / 本地上传 |
| 封面制作 | 文字配图或 AI 生成封面 |
| 自动发布 | Playwright 图文发布 |
| 账号管理 | 多账号切换，登录状态持久化 |
| 选题策略 | 根据主题、城市、图文/视频形态生成热门角度、封面方案、标签和视频预案 |
| 趋势采集 | 站内搜索文本、公开榜单文本、关键词热度、历史发布结果汇总成选题候选 |
| 标题优化 | 按领域生成标题候选，支持发布前自动优化标题 |

## 完整流程

```
1. 选题策略 → 判断热门角度、素材方式、标题和标签
2. 登录处理 → 未登录则手机号短信登录
3. 根据主题生成文案 → 标题 + 正文 + 标签
4. 获取图片 → AI 生图优先；需要事实背书时补充官方网页截图或真实信息源；再按信息图排版 / 网页搜索 / 本地上传补充。封面必须按 1080x1440 生成，正文内容放入中部安全区，底部至少保留 120px，避免小红书预览按钮和裁剪遮挡。封面不要出现 `#话题`，话题只放正文末尾交给发布器输入。
标题规则：避免单调的“xxx了”结尾，不用“开始xx了”作为默认标题；优先使用“别只看… / 门槛在… / 为什么值得盯 / 背后的新信号 / 真正难在…”这类有判断、有悬念的标题。
话题规则：发布器先输入正文；正文完成后移动到正文末尾并插入两个换行，再点击「# 话题」按钮逐个添加话题。只接受完全匹配候选；找不到完全匹配时跳过并记录 `topic_skipped_no_exact`，不要用 Enter 兜底，避免话题变成正文纯文本、插进正文中间或误选相近词。
5. 浏览器发布 → 上传图文 → 填写标题正文 → 点击发布
6. 截图确认 → 保存发布结果
```

## 配置说明

### Playwright 发布
默认使用 `xhs_playwright_publish.cjs`。它会启动可见 Chrome，使用持久化 profile 保存登录态；首次运行如果检测到未登录，会提示输入手机号，自动点击发送验证码，然后等待输入短信验证码。图文发布要求传入至少一张本地图片。

### 内容策略
`xhs_content_strategy.py` 负责输出热门选题 brief。它不直接联网，但支持 `--trend-note` 注入外部热点观察，后续视频发布会复用其中的 `video_plan`。

### 文案模板
位置：`config/xhs-copywriting.yaml`

### 封面模板
位置：`config/xhs-covers.yaml`

## 输出目录

所有输出保存在：`~/.openclaw/workspace/output/`

- `copywriting_*.md` - 生成的文案
- `xhs_before_*.png` - 发布前截图
- `xhs_after_*.png` - 发布后截图
- `publish_result_*.json` - 发布结果

## 安全与合规

- 发布频率：建议每日≤3 篇
- 发布时间：07:00-09:00 / 12:00-13:00 / 19:00-22:00
- 内容原创：AI 生成内容需人工审核
- 版权合规：网页图片需注意版权

## 故障排查

### 登录二维码不显示
- 清除浏览器 Cookie 后重试
- 确认网络连接正常

### 发布失败
- 检查浏览器 profile 是否启用
- 确认账号登录状态
- 查看输出目录中的截图和日志

## 更新日志

### v1.0 (2026-05-09)
- 初始版本
- 整合登录、文案、图片、发布全流程
- 支持一键自动发布

### v1.1 (2026-05-09)
- 新增 Playwright 图文发布流程
- 移除对 OpenClaw browser 命令的运行依赖
- 发布流程验证点：切换“上传图文”tab、文件选择器上传、填写标题正文、提交后检测 `published=true`

### v1.2 (2026-05-09)
- 未登录时改为手机号短信登录：提示手机号、点击发送验证码、等待输入验证码
- 新增 `xhs_content_strategy.py`，沉淀当前小红书图文/视频选题打法
- 图片素材策略扩展为 AI 生成、网页搜索、页面截图、本地图片四类

### v1.3 (2026-05-09)
- Playwright 成为唯一发布与登录路径
- `check-login` 和 `login` 均走 Playwright 手机号验证码流程

# 小红书全自动发布技能

## 一键发布

```bash
python xhs_auto.py --topic "天气" --images /path/to/image.png --auto-publish --browser-method playwright
```

## 文件结构

```
xiaohongshu/
├── SKILL.md              # 技能说明
├── xhs_auto.py           # 主脚本（一键发布）
├── xhs_playwright_publish.cjs # Playwright 图文发布器
├── xhs_title_optimizer.py # 标题候选与标题优化
├── xhs_content_strategy.py # 选题、封面、标签、视频预案
├── image_capture.py      # 图片截取
└── config/
    └── xhs-copywriting.yaml  # 文案模板
```

## 常用命令

```bash
# 一键发布（自动登录 + 生成内容 + 发帖）
python xhs_auto.py --topic "天气" --images /path/to/image.png --auto-publish --browser-method playwright

# 只生成选题与素材策略
python xhs_auto.py --action plan --topic "上海天气" --city "上海" --format note --image-method auto

# 趋势采集：支持通用领域，不限城市
python xhs_auto.py --action trends --domain "ai" --keywords "AI安全" "智能体" "模型评测"

# 标题候选生成
python xhs_auto.py --action titles --domain "ai" --topic "语音AI" --content-file copy.md

# 发布前自动优化标题
python xhs_auto.py --title "语音AI开始办事了" --content-file copy.md --images cover.png --auto-publish --browser-method playwright --domain ai --optimize-title

# 真人刷站内搜索，采集页面文本，再生成选题候选
python xhs_auto.py --action trends --domain "travel" --live-xhs --keywords "小众旅行" "高铁直达" "错峰出行"

# 从网页截取图片并发布
python xhs_auto.py --topic "美景" --url "https://example.com" --capture-images --auto-publish

# 检查登录状态
python xhs_auto.py --action check-login

# 仅生成文案（不发布）
python xhs_auto.py --topic "美食" --dry-run
```

## 前置条件

1. Node.js 已安装
2. Playwright Core 可用
3. Chrome 已安装
4. 小红书账号（首次会用手机号短信登录）

## 登录流程

Playwright 发布器检测到未登录时，会提示输入手机号，自动点击“发送验证码”，然后等待输入短信验证码。也可以提前传入手机号：

```bash
python xhs_auto.py --topic "天气" --images cover.png --auto-publish --browser-method playwright --login-phone <PHONE_NUMBER>

# 只登录，不发布
python xhs_auto.py --action login --browser-method playwright --login-phone <PHONE_NUMBER>
```

## 内容策略

先用 `--action plan` 生成 brief，再决定图文或视频内容。素材方式支持：

- `auto`：优先 AI 生成图；需要事实背书时补充官方网页截图或真实信息源；再考虑信息图排版、本地图片或网页素材
- `ai`：AI 生成图
- `web`：网页搜索图片
- `screenshot`：网页截图
- `local`：本地图片

封面规范：默认 1080x1440，核心标题和信息卡放在中部安全区；底部至少保留 120px 空白，避免小红书预览按钮、话题区或裁剪遮挡。信息图最多放 2-3 个关键点，超出的信息写进正文。封面不要出现 `#话题`，话题只放正文末尾。

标题规范：不要用“xxx了”“开始xx了”这类单调结尾；优先生成有判断和悬念的标题，如“别只看…，先看…”“真正难在…”“背后的新信号”。

话题规范：发布器先输入正文；正文完成后移动到正文末尾并插入两个换行，再点击「# 话题」按钮逐个添加话题。只接受完全匹配候选；如果没有完全匹配，记录 `topic_skipped_no_exact` 并跳过，避免把相近话题或残留文字写成正文纯文本。

## 输出目录

默认输出保存在：`~/.openclaw/workspace/output/`；没有权限时策略模块会回退到当前目录的 `xhs-output/`。

- 文案：`copywriting_*.md`
- 截图：`xhs_before_*.png`
- 结果：`publish_result_*.json`

const fs = require("node:fs");
const path = require("node:path");
let chromium;
try {
  ({ chromium } = require("playwright-core"));
} catch (_) {
  if (!process.env.PLAYWRIGHT_CORE_PATH) {
    throw new Error("playwright-core is not installed. Run npm install playwright-core or set PLAYWRIGHT_CORE_PATH.");
  }
  ({ chromium } = require(process.env.PLAYWRIGHT_CORE_PATH));
}

function argValue(name, fallback = "") {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) return fallback;
  return process.argv[index + 1];
}

function argList(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return [];
  const values = [];
  for (let i = index + 1; i < process.argv.length; i += 1) {
    if (process.argv[i].startsWith("--")) break;
    values.push(process.argv[i]);
  }
  return values;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  const keywords = argList("--keywords");
  const outFile = argValue("--out-file", path.join(process.cwd(), "xhs-live-notes.txt"));
  const profileDir = argValue("--profile-dir", path.join(process.cwd(), "xhs-playwright-profile"));
  const chromePath = argValue("--chrome-path", "C:/Program Files/Google/Chrome/Application/chrome.exe");
  const limit = Number(argValue("--limit", "12"));

  if (!keywords.length) {
    throw new Error("Missing --keywords");
  }

  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: chromePath,
    headless: false,
    viewport: { width: 1365, height: 900 },
    args: ["--disable-blink-features=AutomationControlled"]
  });
  const page = context.pages()[0] || await context.newPage();
  page.setDefaultTimeout(12000);

  const lines = [];
  for (const keyword of keywords) {
    const url = `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}`;
    await page.goto(url, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    for (let i = 0; i < 4; i += 1) {
      await page.mouse.wheel(0, 900);
      await sleep(1200);
    }

    const texts = await page.locator("body").innerText({ timeout: 8000 }).catch(() => "");
    const candidates = texts
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length >= 4 && line.length <= 80)
      .filter((line) => !["登录", "发现", "搜索", "首页", "消息", "我"].includes(line));

    lines.push(`# keyword: ${keyword}`);
    for (const line of candidates.slice(0, limit)) {
      lines.push(line);
    }
    lines.push("");
  }

  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, lines.join("\n"), "utf-8");
  console.log(`live_xhs_notes=${outFile}`);
  await context.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

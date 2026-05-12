const path = require("node:path");
const fs = require("node:fs");
const readline = require("node:readline/promises");
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

function hasFlag(name) {
  return process.argv.includes(name);
}

function normalizeText(text) {
  if (!text) return "";
  return text
    .replace(/\\r\\n/g, "\n")
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, " ")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitBodyAndTopicTags(content, tags) {
  const tagPattern = /#[\p{Script=Han}A-Za-z0-9_\-·.]+/gu;
  const collected = [];
  const bodyLines = [];
  for (const line of normalizeText(content).split("\n")) {
    const found = line.match(tagPattern) || [];
    const withoutTags = line.replace(tagPattern, "").trim();
    if (found.length && !withoutTags) {
      collected.push(...found);
      continue;
    }
    bodyLines.push(line);
  }
  collected.push(...(normalizeText(tags).match(tagPattern) || []));
  const seen = new Set();
  const topicTags = [];
  for (const tag of collected) {
    if (!seen.has(tag)) {
      seen.add(tag);
      topicTags.push(tag);
    }
  }
  return {
    body: normalizeText(bodyLines.join("\n")),
    topicTags,
  };
}

async function promptInput(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    const answer = await rl.question(question);
    return answer.trim();
  } finally {
    rl.close();
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

async function screenshot(page, outDir, name) {
  fs.mkdirSync(outDir, { recursive: true });
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: true });
  console.log(`screenshot=${file}`);
  return file;
}

async function clickText(page, text, timeout = 5000) {
  const locator = page.getByText(text, { exact: false }).first();
  await locator.waitFor({ state: "visible", timeout });
  await locator.click();
}

async function fillFirstAvailable(page, selectors, value, label) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    try {
      await locator.waitFor({ state: "visible", timeout: 3000 });
      await locator.click();
      await locator.fill(value);
      console.log(`filled_${label}=${selector}`);
      return true;
    } catch (_) {}
  }
  return false;
}

async function typeIntoContentEditable(page, value) {
  const candidates = [
    '[contenteditable="true"]',
    ".ql-editor",
    ".ProseMirror",
    'textarea[placeholder*="正文"]',
    'textarea[placeholder*="描述"]',
    'textarea[placeholder*="添加正文"]'
  ];
  for (const selector of candidates) {
    const locator = page.locator(selector).last();
    try {
      await locator.waitFor({ state: "visible", timeout: 3000 });
      await locator.click();
      await page.keyboard.insertText(value);
      console.log(`filled_body=${selector}`);
      return true;
    } catch (_) {}
  }
  return false;
}

async function clickTopicSuggestion(page, tag) {
  const label = tag.replace(/^#/, "");
  const exactPattern = new RegExp(`^#?\\s*${escapeRegExp(label)}(?:\\s|$)`);
  const candidates = [
    page.locator('[role="option"]').filter({ hasText: exactPattern }).first(),
    page.locator('[class*="suggest"]').filter({ hasText: exactPattern }).first(),
    page.locator('[class*="popover"]').filter({ hasText: exactPattern }).first(),
    page.locator('[class*="topic"]').filter({ hasText: exactPattern }).first()
  ];
  for (const locator of candidates) {
    try {
      await locator.waitFor({ state: "visible", timeout: 1200 });
      await locator.click({ timeout: 900 });
      console.log(`topic_selected=${tag}`);
      return true;
    } catch (_) {}
  }
  return false;
}

async function clickTopicButton(page) {
  const candidates = [
    page.locator("button").filter({ hasText: /^#?\s*话题\s*$/ }).first(),
    page.getByText("# 话题", { exact: true }).first(),
    page.getByText("话题", { exact: true }).first()
  ];
  for (const locator of candidates) {
    try {
      await locator.waitFor({ state: "visible", timeout: 1200 });
      await locator.click({ timeout: 1200 });
      return true;
    } catch (_) {}
  }
  return false;
}

async function typeTopicTags(page, tags) {
  if (!tags.length) return;
  await page.keyboard.press("Control+End").catch(() => {});
  await sleep(250);
  await page.keyboard.insertText("\n\n");
  await sleep(250);
  for (const tag of tags) {
    const label = tag.replace(/^#/, "");
    await page.keyboard.press("Escape").catch(() => {});
    await sleep(250);
    const opened = await clickTopicButton(page);
    if (!opened) {
      console.log(`topic_button_missing=${tag}`);
      continue;
    }
    await sleep(500);
    await page.keyboard.type(label, { delay: 90 });
    await sleep(1100);
    const selected = await clickTopicSuggestion(page, tag);
    if (!selected) {
      await page.keyboard.press("Escape").catch(() => {});
      console.log(`topic_skipped_no_exact=${tag}`);
    } else {
      await page.keyboard.press("Escape").catch(() => {});
    }
    await sleep(500);
  }
}

async function uploadFirstImage(page, imagePath) {
  try {
    const chooserPromise = page.waitForEvent("filechooser", { timeout: 5000 });
    try {
      await page.getByText("上传图片", { exact: false }).click({ timeout: 3000 });
    } catch (_) {
      await page.mouse.click(787, 485);
    }
    const chooser = await chooserPromise;
    await chooser.setFiles(imagePath);
    console.log(`uploaded_by_filechooser=${imagePath}`);
    return true;
  } catch (_) {
    const fileInput = page.locator('input[type="file"]').last();
    await fileInput.setInputFiles(imagePath);
    console.log(`uploaded_by_input=${imagePath}`);
    return true;
  }
}

async function fillLoginField(page, selectors, value, label) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    try {
      await locator.waitFor({ state: "visible", timeout: 3000 });
      await locator.click();
      await locator.fill(value);
      console.log(`login_${label}=${selector}`);
      return true;
    } catch (_) {}
  }
  return false;
}

async function clickLoginText(page, texts, label) {
  for (const text of texts) {
    try {
      await page.getByText(text, { exact: false }).first().click({ timeout: 3000 });
      console.log(`login_click_${label}=${text}`);
      return true;
    } catch (_) {}
  }
  return false;
}

async function loginWithSms(page, outDir, initialPhone) {
  console.log("login_required=true");
  let phone = initialPhone || process.env.XHS_LOGIN_PHONE || "";
  if (!phone) {
    phone = await promptInput("请输入小红书登录手机号：");
  }
  if (!phone) {
    throw new Error("Missing phone number for SMS login.");
  }

  await clickLoginText(page, ["短信登录", "手机号登录", "手机登录"], "sms_tab");
  const phoneFilled = await fillLoginField(page, [
    'input[placeholder*="手机号"]',
    'input[placeholder*="手机"]',
    'input[type="tel"]',
    'input[type="text"]'
  ], phone, "phone");
  if (!phoneFilled) {
    await page.keyboard.insertText(phone);
    console.log("login_phone=keyboard_fallback");
  }

  await clickLoginText(page, ["发送验证码", "获取验证码", "获取短信验证码"], "send_code");
  await screenshot(page, outDir, "02-sms-code-sent.png");

  const code = await promptInput("请输入收到的短信验证码：");
  if (!code) {
    throw new Error("Missing SMS verification code.");
  }

  const codeFilled = await fillLoginField(page, [
    'input[placeholder*="验证码"]',
    'input[placeholder*="短信"]',
    'input[type="number"]'
  ], code, "code");
  if (!codeFilled) {
    await page.keyboard.press("Tab");
    await page.keyboard.insertText(code);
    console.log("login_code=keyboard_fallback");
  }

  await clickLoginText(page, ["登录", "同意并登录", "进入"], "submit");
  await page.waitForFunction(() => {
    const text = document.body.innerText;
    return !text.includes("短信登录") && !text.includes("手机号") && !text.includes("验证码");
  }, null, { timeout: 120000 });
  await screenshot(page, outDir, "02-after-sms-login.png");
}

async function main() {
  const title = normalizeText(argValue("--title"));
  const content = normalizeText(argValue("--content"));
  const tags = normalizeText(argValue("--tags"));
  const loginPhone = argValue("--login-phone");
  const loginOnly = hasFlag("--login-only");
  const images = argList("--images");
  const headless = hasFlag("--headless");
  const workspace = argValue("--workspace", process.cwd());
  const outDir = argValue("--out-dir", path.join(workspace, "xhs-output"));
  const profileDir = argValue("--profile-dir", path.join(workspace, "xhs-playwright-profile"));
  const chromePath = argValue("--chrome-path", "C:/Program Files/Google/Chrome/Application/chrome.exe");

  if (!loginOnly && (!title || !content)) {
    throw new Error("Missing required --title or --content.");
  }
  if (!loginOnly && !images.length) {
    throw new Error("Playwright publisher requires at least one local image path.");
  }
  const imagePath = images.length ? path.resolve(images[0]) : "";
  if (!loginOnly && !fs.existsSync(imagePath)) {
    throw new Error(`Image not found: ${imagePath}`);
  }

  const context = await chromium.launchPersistentContext(profileDir, {
    executablePath: chromePath,
    headless,
    viewport: { width: 1365, height: 900 },
    acceptDownloads: true,
    args: ["--disable-blink-features=AutomationControlled"]
  });
  const page = context.pages()[0] || await context.newPage();
  page.setDefaultTimeout(10000);

  await page.goto("https://creator.xiaohongshu.com", { waitUntil: "domcontentloaded" });
  await sleep(3000);
  await screenshot(page, outDir, "01-creator-home.png");

  const bodyText = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
  if (["短信登录", "手机号", "验证码", "发送验证码", "登录"].some((hint) => bodyText.includes(hint))) {
    await loginWithSms(page, outDir, loginPhone);
    await page.goto("https://creator.xiaohongshu.com", { waitUntil: "domcontentloaded" });
    await sleep(3000);
  }

  if (loginOnly) {
    const text = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
    const loggedIn = !["短信登录", "手机号", "验证码", "发送验证码"].some((hint) => text.includes(hint));
    console.log(`login_success=${loggedIn}`);
    await screenshot(page, outDir, "login-result.png");
    await context.close();
    return;
  }

  let clickedPublish = false;
  for (const text of ["发布笔记", "发布图文", "发布", "上传图文"]) {
    try {
      await clickText(page, text, 4000);
      clickedPublish = true;
      console.log(`clicked_publish_entry=${text}`);
      break;
    } catch (_) {}
  }
  if (!clickedPublish) {
    await page.goto("https://creator.xiaohongshu.com/publish/publish", { waitUntil: "domcontentloaded" });
  }
  await sleep(4000);

  try {
    await page.getByText("上传图文", { exact: true }).click({ timeout: 5000 });
  } catch (_) {
    await page.mouse.click(435, 102);
  }
  await sleep(3000);
  await screenshot(page, outDir, "03-publish-page.png");

  await uploadFirstImage(page, imagePath);
  await sleep(8000);
  for (const text of ["下一步", "去发布", "确定"]) {
    try {
      await clickText(page, text, 3000);
      await sleep(5000);
      break;
    } catch (_) {}
  }
  await screenshot(page, outDir, "04-after-upload.png");

  const titleFilled = await fillFirstAvailable(page, [
    'input[placeholder*="标题"]',
    'textarea[placeholder*="标题"]',
    '[contenteditable="true"][placeholder*="标题"]'
  ], title, "title");
  if (!titleFilled) {
    await page.keyboard.press("Tab");
    await page.keyboard.insertText(title);
    console.log("filled_title=keyboard_fallback");
  }

  const splitContent = splitBodyAndTopicTags(content, tags);
  const editorBodyText = splitContent.body.trimEnd();
  const bodyFilled = await typeIntoContentEditable(page, editorBodyText);
  if (!bodyFilled) {
    await page.keyboard.press("Tab");
    await page.keyboard.insertText(editorBodyText);
    console.log("filled_body=keyboard_fallback");
  }
  await typeTopicTags(page, splitContent.topicTags);
  await sleep(2000);
  await screenshot(page, outDir, "05-filled-draft.png");

  await page.keyboard.press("Escape").catch(() => {});
  await sleep(1000);
  await page.mouse.wheel(0, 1600).catch(() => {});
  await sleep(1000);

  for (const locator of [
    page.getByRole("button", { name: "发布", exact: true }),
    page.locator("button.publishBtn"),
    page.locator("button:has-text('发布')"),
    page.getByText("发布", { exact: true }),
    page.locator("button").filter({ hasText: "发布" })
  ]) {
    try {
      const first = locator.first();
      await first.waitFor({ state: "visible", timeout: 3000 });
      await first.click();
      console.log("submitted=true");
      await sleep(8000);
      await screenshot(page, outDir, "06-after-submit.png");
      break;
    } catch (_) {}
  }

  const finalUrl = page.url();
  console.log(`final_url=${finalUrl}`);
  const published = finalUrl.includes("published=true") || finalUrl.includes("/publish/success");
  console.log(`published=${published}`);
  await context.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

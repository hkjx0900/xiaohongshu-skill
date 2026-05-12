# Xiaohongshu Skill Install

Copy this directory to your Codex skills folder:

```powershell
Copy-Item -Recurse -Force . "$env:USERPROFILE\.codex\skills\xiaohongshu"
```

Dependencies:

```bash
npm install playwright-core
```

If `playwright-core` is installed in a custom location, set:

```powershell
$env:PLAYWRIGHT_CORE_PATH="C:\path\to\node_modules\playwright-core"
```

The skill stores browser login state only at runtime in `xhs-playwright-profile/`, which is intentionally excluded from Git.

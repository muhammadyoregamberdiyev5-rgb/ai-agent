---
name: agent-browser
description: Browser automation CLI for AI agents using agent-browser (Vercel Labs). Fast native Rust CLI with accessibility-tree based element selection. Use when you need headless browser control from the terminal — navigate, click, fill forms, screenshot, batch commands, AI chat mode.
tags: [browser, automation, cli, playwright, chrome, ai-agent]
---

# agent-browser

Browser automation CLI for AI agents by Vercel Labs.
Repo: https://github.com/vercel-labs/agent-browser

## Installation

### npm (recommended, already installed globally)
```
npm install -g agent-browser
agent-browser install   # download Chrome for Testing (first time only)
```

### Homebrew (macOS)
```
brew install agent-browser
agent-browser install
```

### Cargo (Rust)
```
cargo install agent-browser
agent-browser install
```

### Update
```
agent-browser upgrade
```

Chrome is stored at: ~/.agent-browser/browsers/chrome-<version>/

## Quick Start

```bash
agent-browser open example.com
agent-browser snapshot          # accessibility tree with @eN refs
agent-browser click @e2         # click element by ref
agent-browser fill @e3 "text"   # clear + fill input by ref
agent-browser screenshot page.png
agent-browser close
```

## Core Commands

```bash
agent-browser open <url>              # navigate (aliases: goto, navigate)
agent-browser snapshot                # accessibility tree with refs (best for AI)
agent-browser snapshot -i             # interactive snapshot (live)
agent-browser click <sel>             # click element
agent-browser fill <sel> <text>       # clear and fill
agent-browser type <sel> <text>       # type into element
agent-browser press <key>             # press key (Enter, Tab, Control+a)
agent-browser scroll <dir> [px]       # scroll up/down/left/right
agent-browser screenshot [path]       # screenshot (--full for full page)
agent-browser screenshot --annotate   # annotated with numbered labels
agent-browser eval <js>               # run JavaScript
agent-browser wait <selector>         # wait for element
agent-browser wait --text "text"      # wait for text
agent-browser wait <ms>               # wait milliseconds
agent-browser close                   # close browser
```

## Get Info

```bash
agent-browser get text <sel>
agent-browser get html <sel>
agent-browser get value <sel>
agent-browser get title
agent-browser get url
```

## Semantic Locators (find)

```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "test@test.com"
agent-browser find nth 2 "a" text
```

## Batch Execution

```bash
# argument mode
agent-browser batch "open https://example.com" "snapshot -i" "screenshot"

# stdin JSON mode
echo '[["open","https://example.com"],["snapshot"],["screenshot","out.png"]]' | agent-browser batch --json
```

## AI Chat Mode

```bash
agent-browser chat "Go to example.com and take a screenshot"  # single-shot
agent-browser chat                                              # interactive REPL
```

## Notes & Pitfalls

- Always run `agent-browser install` once after install to download Chrome.
- Chrome stored at ~/.agent-browser/browsers/
- Selectors: prefer @eN refs from snapshot for AI use; CSS selectors also work.
- On Linux: `agent-browser install --with-deps` to install system dependencies.
- Requires network proxy on restricted networks (set https_proxy before install).

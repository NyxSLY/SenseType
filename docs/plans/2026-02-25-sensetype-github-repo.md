# SenseType GitHub Repo Setup — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename project from WhisperInput to SenseType, prepare all files, and publish to GitHub as `NyxSLY/SenseType`.

**Architecture:** In-place rename of `whisper_input/` → `sensetype/`, update all internal references, add standard open-source files (README, LICENSE, .gitignore), initialize git, push to GitHub.

**Tech Stack:** git, gh CLI, Python packaging conventions

---

### Task 1: Create .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Write .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
*.egg

# Environment
.env
.venv/
env/

# micromamba artifacts (bundled for deployment convenience, not source)
micromamba.exe
micromamba.tar.bz2
info/
Library/

# IDE
.vscode/
.idea/

# Claude Code (AI development instructions — not part of the project)
.claude/
CLAUDE.md
sensetype/CLAUDE.md

# Internal notes
技术要点.md

# Audio recordings
*_audio/

# OS
Thumbs.db
.DS_Store
```

**Step 2: Verify**

Run: `cat .gitignore` — confirm it exists.

---

### Task 2: Rename package `whisper_input/` → `sensetype/`

**Files:**
- Rename: `whisper_input/` → `sensetype/`
- Delete: `sensetype/__pycache__/` (stale bytecode)
- Delete: `sensetype/CLAUDE.md` (AI-internal, not for repo)

**Step 1: Rename the directory**

```bash
mv whisper_input sensetype
rm -rf sensetype/__pycache__
rm -f sensetype/CLAUDE.md
```

**Step 2: Verify**

Run: `ls sensetype/` — should show all .py files.

---

### Task 3: Update internal references — brand name

**Files:**
- Modify: `sensetype/main.py` (line 31: "WhisperInput" → "SenseType")
- Modify: `sensetype/tray.py` (lines 56, 58, 68: "WhisperInput" → "SenseType")
- Modify: `sensetype/recorder.py` (line 28: `whisper_input_audio` → `sensetype_audio`)
- Modify: `requirements.txt` (line 1 comment)

**Step 1: Update main.py**

Line 31: `"=== WhisperInput 本地语音输入 ==="` → `"=== SenseType 本地语音输入 ==="`

**Step 2: Update tray.py**

Three occurrences of "WhisperInput" → "SenseType" (name, title strings)

**Step 3: Update recorder.py**

Line 28: `"whisper_input_audio"` → `"sensetype_audio"`

**Step 4: Update requirements.txt**

Line 1 comment: `# WhisperInput 依赖` → `# SenseType 依赖`

**Step 5: Verify**

Run: `grep -r "WhisperInput\|whisper_input" sensetype/` — should return nothing.

---

### Task 4: Update documentation files

**Files:**
- Modify: `ARCHITECTURE.md` — all "WhisperInput" → "SenseType", `whisper_input/` → `sensetype/`
- Modify: `TODO.md` — "WhisperInput" → "SenseType"
- Modify: `Windows平台部署指南.md` — `python -m whisper_input` → `python -m sensetype`, rename to `docs/deployment-guide-zh.md`

**Step 1: Update ARCHITECTURE.md**

Replace all "WhisperInput" → "SenseType" and `whisper_input/` → `sensetype/`.

**Step 2: Update TODO.md**

Line 1: `# WhisperInput TODO` → `# SenseType TODO`

**Step 3: Move and update deployment guide**

Move `Windows平台部署指南.md` → `docs/deployment-guide-zh.md`, update `python -m whisper_input` → `python -m sensetype`.

**Step 4: Verify**

Run: `grep -r "whisper_input\|WhisperInput" *.md docs/` — should return nothing.

---

### Task 5: Create LICENSE (MIT)

**Files:**
- Create: `LICENSE`

**Step 1: Write MIT license**

Use current year (2026), copyright holder: "SenseType Contributors".

---

### Task 6: Create README.md (English)

**Files:**
- Create: `README.md`

**Content outline:**
1. Project name + one-line description + badges
2. Demo GIF placeholder
3. Why SenseType (vs Whisper-based tools) — speed/accuracy comparison table
4. Features list
5. Quick Start (3 steps: install micromamba, install deps, run)
6. Configuration table
7. Architecture diagram (ASCII)
8. Comparison with alternatives
9. Roadmap
10. License

Key selling points to emphasize:
- **15x faster** than Whisper-Large (SenseVoice NAR architecture)
- **15-20% lower CER** for Chinese
- Built-in VAD + ITN (punctuation)
- Auto GPU/CPU detection (4GB VRAM threshold)
- Modular frontend (replaceable overlay UI)
- Pure Win32 API clipboard (no pywin32 dependency)

---

### Task 7: Create README_zh.md (Chinese)

**Files:**
- Create: `README_zh.md`

Translated version of README.md with Chinese-specific context. Link from main README.

---

### Task 8: Initialize git repo and push to GitHub

**Step 1: Authenticate gh CLI**

```bash
gh auth login
```

**Step 2: Initialize git**

```bash
git init
git add .
git commit -m "Initial commit: SenseType — local voice typing with SenseVoice"
```

**Step 3: Create GitHub repo and push**

```bash
gh repo create NyxSLY/SenseType --public --description "Local voice typing for Windows powered by SenseVoice. 15x faster than Whisper for Chinese input." --source . --push
```

---

## Execution Notes

- Tasks 1-7 are file operations, can be parallelized where independent.
- Task 8 requires gh auth — user interaction needed.
- CLAUDE.md stays locally but is gitignored — project-internal AI instructions preserved.

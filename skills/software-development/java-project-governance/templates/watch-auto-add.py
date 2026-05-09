#!/usr/bin/env python3
"""
Multi-repo auto git-add monitor with structure checking.

Usage:
    python3 scripts/watch-auto-add.py          # foreground
    nohup python3 scripts/watch-auto-add.py > /tmp/watch-auto-add.log 2>&1 &  # background
"""

import os
import sys
import time
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "check-structure.py")

YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

# {repo_name: set(rel_filepath)}
seen_files = {}


def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"{CYAN}[{ts}]{RESET} {msg}")


def find_git_repos():
    repos = []
    try:
        for entry in os.listdir(PROJECT_ROOT):
            repo_path = os.path.join(PROJECT_ROOT, entry)
            git_dir = os.path.join(repo_path, ".git")
            if os.path.isdir(repo_path) and os.path.isdir(git_dir):
                repos.append(repo_path)
    except Exception:
        pass
    return repos


def get_git_status(repo_path):
    try:
        output = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            text=True,
        )
        untracked = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            filepath = line[3:]
            if status == "??":
                untracked.append(filepath)
        return untracked
    except subprocess.CalledProcessError:
        return []


def git_add(repo_path, filepath):
    try:
        subprocess.run(
            ["git", "add", filepath],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_files(files):
    if not files:
        return None
    cmd = [sys.executable, CHECK_SCRIPT] + files
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0 and result.stdout:
            return result.stdout
    except Exception as e:
        return str(e)
    return None


def scan_repo(repo_path):
    repo_name = os.path.basename(repo_path)
    untracked = get_git_status(repo_path)

    if repo_name not in seen_files:
        seen_files[repo_name] = set()

    new_java_files = []
    for f in untracked:
        full = os.path.join(repo_path, f)
        if f.endswith(".java") and f not in seen_files[repo_name]:
            new_java_files.append(full)
        if git_add(repo_path, f):
            indicator = f"{GREEN}✅ [{repo_name}] 自动 git add:{RESET}"
            suffix = " (非Java文件)" if not f.endswith(".java") else ""
            log(f"{indicator} {f}{suffix}")

    if new_java_files:
        issues = check_files(new_java_files)
        if issues:
            print(issues)
        for f in new_java_files:
            rel = os.path.relpath(f, repo_path)
            seen_files[repo_name].add(rel)


def main():
    repos = find_git_repos()
    if not repos:
        log(f"❌ 未在 {PROJECT_ROOT} 下找到 Git 仓库")
        return

    log(f"👁️ 开始监控 {len(repos)} 个仓库")
    log("自动 git add 已启动，按 Ctrl+C 停止...")
    log("规则: 检查新增 Java 文件符合项目结构规范，不会自动 commit/push\n")

    while True:
        try:
            for repo in repos:
                scan_repo(repo)
            time.sleep(5)
        except KeyboardInterrupt:
            log("🛝 监控已停止")
            break
        except Exception as e:
            log(f"错误: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()

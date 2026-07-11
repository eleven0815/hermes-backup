#!/usr/bin/env python3
"""
Java layered-architecture structure checker.

Usage:
    python3 scripts/check-structure.py <file1.java> <file2.java> ...
    python3 scripts/check-structure.py --git-staged   # checks newly added files in current repo
"""

import os
import re
import sys
import subprocess

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Adjust these to match your project's package conventions
LAYER_PREFIXES = {
    "service": "com.yonyou.dcs.",
    # Everything else uses this:
    "default": "com.yonyou.oem.",
}

# Derive project root from script location: scripts/ -> ../
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_package_from_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("package "):
                    return line.replace("package ", "").rstrip(";").strip()
    except Exception:
        pass
    return None


def get_package_from_path(filepath):
    rel_path = os.path.relpath(filepath, PROJECT_ROOT)
    parts = rel_path.split(os.sep)
    for i, part in enumerate(parts):
        if part == "java" and i >= 2 and parts[i - 1] == "main" and parts[i - 2] == "src":
            pkg_parts = parts[i + 1 : -1]
            return ".".join(pkg_parts)
    return None


def detect_submodule_type(filepath):
    parts = filepath.split(os.sep)
    for part in parts:
        if part.startswith("dev-"):
            segments = part.split("-")
            if len(segments) >= 2:
                return segments[-1]  # e.g., api, service, app, infrastructure
    return None


def check_file(filepath):
    issues = []
    rel_path = os.path.relpath(filepath, PROJECT_ROOT)

    if not filepath.endswith(".java"):
        return issues
    if "-be" not in rel_path or "src/main/java" not in rel_path.replace("\\", "/"):
        return issues

    file_package = get_package_from_file(filepath)
    path_package = get_package_from_path(filepath)
    submodule_type = detect_submodule_type(filepath)

    if not submodule_type:
        return issues

    # Rule 1: package declaration matches directory path
    if file_package and path_package and file_package != path_package:
        issues.append(
            f"  ❌ package 声明与目录路径不一致: "
            f"声明 '{file_package}' vs 路径 '{path_package}'"
        )

    # Rule 2: package prefix matches submodule type
    expected_prefix = LAYER_PREFIXES.get("service") if submodule_type == "service" else LAYER_PREFIXES.get("default")
    if expected_prefix and file_package and not file_package.startswith(expected_prefix):
        issues.append(
            f"  ❌ 包名前缀不符: '{file_package}' "
            f"(期望以 '{expected_prefix}' 开头, 子模块: {submodule_type})"
        )

    # Rule 3: layer responsibility constraints
    if submodule_type == "service":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            forbidden_patterns = [
                (r"import\s+org\.apache\.ibatis", "MyBatis (SQL)"),
                (r"import\s+tk\.mybatis", "tk.MyBatis (SQL)"),
                (r"import\s+org\.springframework\.jdbc", "Spring JDBC"),
                (r"import\s+redis\.clients", "Redis Client"),
                (r"import\s+org\.springframework\.data\.redis", "Spring Redis"),
                (r"import\s+org\.springframework\.amqp", "AMQP/MQ"),
                (r"import\s+org\.apache\.rocketmq", "RocketMQ"),
                (r"@Repository", "@Repository 注解"),
                (r"@Mapper", "@Mapper 注解"),
            ]
            for pattern, desc in forbidden_patterns:
                if re.search(pattern, content):
                    issues.append(
                        f"  ⚠️  service 层发现禁用引用: {desc} "
                        f"(应放在 infrastructure 层)"
                    )
                    break
        except Exception:
            pass

    if submodule_type == "api":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            forbidden_patterns = [
                (r"@Controller", "@Controller"),
                (r"@RestController", "@RestController"),
                (r"@Service", "@Service"),
                (r"@Repository", "@Repository"),
                (r"@Mapper", "@Mapper"),
            ]
            for pattern, desc in forbidden_patterns:
                if re.search(pattern, content):
                    issues.append(
                        f"  ⚠️  api 层发现禁用注解: {desc} "
                        f"(应放在 app/service/infrastructure 层)"
                    )
                    break
        except Exception:
            pass

    return issues


def check_files(files):
    results = {}
    for f in files:
        if os.path.exists(f):
            issues = check_file(f)
            if issues:
                results[f] = issues
    return results


def get_staged_java_files():
    try:
        output = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=A"],
            text=True,
        )
        # Use cwd for multi-repo compatibility (pre-commit hook runs inside submodule)
        cwd = os.getcwd()
        files = [os.path.join(cwd, f) for f in output.strip().split("\n") if f]
        return [f for f in files if f.endswith(".java")]
    except subprocess.CalledProcessError:
        return []


def print_results(results):
    if not results:
        return False
    print(f"\n{YELLOW}{BOLD}⚠️  项目结构规范检查发现问题{RESET}")
    print("=" * 60)
    for filepath, issues in results.items():
        rel = os.path.relpath(filepath, PROJECT_ROOT)
        print(f"\n{BOLD}📄 {rel}{RESET}")
        for issue in issues:
            print(issue)
    print("\n" + "=" * 60)
    print(f"{YELLOW}请检查上述文件，确认是否符合分层规范后再进行 commit。{RESET}\n")
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--git-staged":
        files = get_staged_java_files()
        results = check_files(files)
        has_issues = print_results(results)
        sys.exit(1 if has_issues else 0)
    elif len(sys.argv) > 1:
        files = [os.path.abspath(f) for f in sys.argv[1:]]
        results = check_files(files)
        print_results(results)
        sys.exit(1 if results else 0)
    else:
        print("Usage:")
        print("  python3 scripts/check-structure.py <file.java> ...")
        print("  python3 scripts/check-structure.py --git-staged")
        sys.exit(1)

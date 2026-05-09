#!/usr/bin/env python3
"""Hermes Skill Curator - 自动归档长期未使用的本地技能"""
import os
import shutil
from datetime import datetime, timedelta

SKILLS_DIR = os.path.expanduser("~/.hermes/skills")
ARCHIVE_DIR = os.path.join(SKILLS_DIR, ".archive")
DAYS_THRESHOLD = 60  # 60天未修改即归档


def get_skill_size(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total += os.path.getsize(fp)
    return total


def main():
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        print(f"📦 Created archive dir: {ARCHIVE_DIR}")

    archived = []

    # 只扫描 local / hub 技能（builtin 在源码目录，不动）
    for root, dirs, files in os.walk(SKILLS_DIR):
        if ARCHIVE_DIR in root:
            continue
        if "SKILL.md" in files:
            skill_md = os.path.join(root, "SKILL.md")
            rel = os.path.relpath(root, SKILLS_DIR)
            mtime = datetime.fromtimestamp(os.path.getmtime(skill_md))
            age_days = (datetime.now() - mtime).days
            size = get_skill_size(root)

            if age_days > DAYS_THRESHOLD:
                dest = os.path.join(ARCHIVE_DIR, rel)
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(root, dest)
                archived.append((rel, age_days, size))

    print(f"\n🧹 Hermes Skill Curator Report ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 50)
    if archived:
        total_size = sum(s for _, _, s in archived)
        print(f"✅ 归档了 {len(archived)} 个技能（共 {total_size/1024:.1f} KB）：")
        for name, age, size in archived:
            print(f"   • {name} | {age} 天未更新 | {size/1024:.1f} KB")
        print(f"\n💡 提示：被归档的技能不再加载到系统提示词中，可显著降低 Token 消耗。")
        print(f"   如需恢复：mv ~/.hermes/skills/.archive/<skill> ~/.hermes/skills/")
    else:
        print("✅ 没有发现超过 60 天未更新的本地技能，无需归档。")

    # 同时输出当前技能统计
    all_skills = []
    for root, dirs, files in os.walk(SKILLS_DIR):
        if ARCHIVE_DIR in root:
            continue
        if "SKILL.md" in files:
            all_skills.append(os.path.relpath(root, SKILLS_DIR))
    print(f"\n📊 当前活跃本地技能数量: {len(all_skills)}")


if __name__ == "__main__":
    main()

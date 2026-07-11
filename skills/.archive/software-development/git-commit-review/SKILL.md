---
name: git-commit-review
description: "Review a specific git commit by hash in a local repository, analyzing cross-file patterns and providing structured feedback."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [git, code-review, commit, diff, quality, java, monorepo]
    related_skills: [github-code-review, requesting-code-review]
---

# Git Commit Review

Review an already-committed git revision by its hash. Useful for post-commit review, understanding a teammate's changes, or auditing a specific commit before cherry-pick/revert.

**This skill vs github-code-review:** `github-code-review` reviews PRs and local uncommitted changes. This skill reviews a committed revision by hash, often in a monorepo with multiple sub-repositories.

## When to Use

- User gives a commit hash: "review commit abc1234"
- User asks "what changed in commit X?"
- Auditing a commit before cherry-pick, revert, or merge
- Reviewing a teammate's committed work before integration
- Working in a monorepo where the commit might be in any sub-repo

## Step 1 — Locate the Commit

If already inside a git repo, try directly. If not, or if this is a monorepo with multiple sub-repositories, search for the commit:

```bash
# Direct check
git cat-file -t <hash> 2>/dev/null

# Search across sub-repos (monorepo)
for d in */.git; do
  repo=$(dirname "$d")
  if git -C "$repo" cat-file -t <hash> 2>/dev/null | grep -q commit; then
    echo "FOUND in: $repo"
  fi
done
```

Then `cd` into the correct repository.

## Step 2 — Get the Big Picture

```bash
# Commit metadata
git log -1 --format="%H%n%an <%ae>%n%ad%n%s%n%b" <hash>

# Files changed with line counts
git show --stat <hash>

# Just file names
git show --name-only <hash>
```

Note the scope. If >50 files or >5,000 lines changed, focus on the most critical files first (controllers, services, database schemas) and note the commit is large.

## Step 3 — Identify Key Files to Review

Prioritize review order:

1. **API/Controller layer** — entry points, URL mappings, auth checks
2. **Service layer** — business logic, transaction boundaries, exception handling
3. **Repository/DAO layer** — SQL queries, transaction propagation, N+1 risks
4. **DTOs/POs/Converters** — data mapping, validation rules, serialization
5. **Database migrations** — schema changes, indexes, data types
6. **Configuration/Constants/Enums** — shared values, magic strings

## Step 4 — Examine Changes File by File

```bash
# Full diff of the commit
git show <hash>

# Specific file
git show <hash> -- path/to/File.java

# Multiple related files
git show <hash> -- "*Controller.java" "*ServiceImpl.java"
```

For each key file, use `read_file` to see the full post-commit state if surrounding context is needed.

## Step 5 — Cross-File Pattern Analysis

The most valuable review insight comes from comparing multiple files for consistency. Check these patterns across the commit:

### 5.1 Exception Handling Consistency

Look at all `catch` blocks in the commit. Are they uniform?

**Red flag:** Some services update the database on exception, others don't, some throw raw RuntimeException without logging.

```java
// Inconsistent examples to watch for:
catch (Exception e) {
    logger.error("...", e);
    repository.updateResponse(id, ..., e.getMessage());  // A: updates DB
    throw new RuntimeException("...", e);
}

catch (Exception e) {
    // repository.updateResponse(...);  // B: commented out!
    throw new RuntimeException("...", e);
}

catch (Exception e) {
    logger.error("...", e);
    throw new RuntimeException("...", e);  // C: no DB update at all
}
```

### 5.2 Hardcoded Strings vs Constants

Check if the same literal appears in multiple files:

```java
// Bad: scattered across services
ci.setSrcsystem("DMS");
ci.setDestsystem("SAP");

// Good: centralized constant
ci.setSrcsystem(SapConstants.SYSTEM_DMS);
ci.setDestsystem(SapConstants.SYSTEM_SAP);
```

Search for repeated literals in the diff:
```bash
git show <hash> | grep "^+" | grep -oE '"[^"]{3,}"' | sort | uniq -c | sort -rn | head -20
```

### 5.3 Transaction Boundaries

In Spring/Java projects, check `@Transactional` usage:

- Is the service method annotated, or only the repository?
- Does repository use `Propagation.REQUIRES_NEW` when it should be `REQUIRED`?
- Are there multiple independent transactions that should be atomic?

### 5.4 Status/Success Judgment Logic

Look for how "success" is determined across the commit:

```java
// Inconsistent:
SapStatusEnum.isSuccess(code)          // A
SapConstants.CODE_SUCCESS.equals(code) // B
"S".equals(code) ? "SUCCESS" : "FAIL"  // C
```

**Rule:** One project should have ONE way to judge API success.

### 5.5 Database Schema Issues (SQL migrations)

For DDL changes, check:

- **Field lengths:** Are all fields `varchar(200)` regardless of actual data length?
- **Indexes:** Are there indexes on fields commonly queried (`status`, `create_time`, business keys)?
- **JSON storage:** Is `TEXT` used when `JSON` type would be better (MySQL 5.7+)?
- **Missing constraints:** Should any fields be `NOT NULL`?

### 5.6 File Formatting Hygiene

```bash
# Check for missing newlines at EOF
git show <hash> | grep "No newline at end of file"
```

### 5.7 Comment Accuracy

```java
/**
 * FICO030B 状态枚举 (STATUS)   <-- Is this REALLY only for FICO030B?
 */
public enum SapStatusEnum { }
```

Comments copied from one file to another often retain the wrong context.

## Step 6 — Present Structured Feedback

Use this format:

```
## Code Review: <commit-short-hash> (<repo-name>)

**提交信息:** <subject>
**作者:** <author>
**规模:** <N> files, +<add>/-<del> lines

---

### 1. 整体评价
2-3 sentences summarizing the commit's purpose and architecture.

### 2. 主要问题 (Critical / Warnings)

| 优先级 | 问题 | 影响文件 |
|--------|------|----------|
| P0 | Exception handling inconsistent across services | *ServiceImpl.java |
| P0 | Success/failure logic uses 3 different patterns | *ServiceImpl.java |
| P1 | Hardcoded "DMS"/"SAP" instead of constants | SapSd021/22... |
| P1 | Repository uses REQUIRES_NEW without Service @Transactional | *RepositoryImpl.java |
| P2 | SQL fields all varchar(200) regardless of actual length | 01_create_*.sql |
| P2 | Missing indexes on status and create_time | 01_create_*.sql |
| P2 | Files missing newline at EOF | Multiple |
| P3 | Enum comment refers to wrong module | SapStatusEnum.java |

### 3. 正面评价
- DTO/PO separation is clean
- Default value filling is uniform across services
- Good use of enum validation for SAP field values

### 4. 建议修复优先级
(Present as a table: Priority | Issue | Files)
```

## Step 7 — Optional: Verify Fixability

If the user wants to fix the issues, help them:

1. Identify which files need changes
2. Check if fixes can be made as a follow-up commit or require amending
3. For monorepos, ensure fixes go to the correct sub-repo

## Step 8 — Bulk Remediation (When User Asks for Fixes)

If the user asks you to fix the issues found in the review, prefer **programmatic batch fixes** when the same pattern appears in 3+ files. Do not hand-edit each file individually.

### 8.1 When to Use Programmatic Fixes

| Approach | When to use |
|----------|-------------|
| Python regex script | Same pattern in 3+ files (imports, string literals, method calls) |
| `sed -i` one-liner | Simple string replacement across many files |
| `patch` tool | Specific hunks you already know the exact diff for |
| Manual edit | One-off logic changes that don't fit a regex pattern |

### 8.2 Batch Fix Workflow

**Step A — Snapshot current state**
```bash
git status --short
git diff --name-only
```

**Step B — Identify target files**
```bash
# Find all files matching a pattern
grep -rl "ci.setSrcsystem(\"DMS\")" c-oem-isscp-common-be/

# Find files missing an import
grep -rl "SapConstants" --include="*.java" . | xargs grep -L "import com.yonyou.oem.common.api.constant.SapConstants;"
```

**Step C — Write a Python script to apply fixes**

Use `execute_code` (not shell loops) for complex multi-rule fixes:

```python
import os, re

service_dir = ".../src/main/java/com/.../service/impl/sap"
files = [f for f in os.listdir(service_dir) if f.endswith('ServiceImpl.java')]

for fname in files:
    fpath = os.path.join(service_dir, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # Rule 1: Add missing import
    if 'SapConstants' in content and 'import ...SapConstants;' not in content:
        content = content.replace(
            'import com.yonyou.oem.common.service.ExternalInterfaceCaller;',
            'import com.yonyou.oem.common.api.constant.SapConstants;\nimport com.yonyou.oem.common.service.ExternalInterfaceCaller;'
        )

    # Rule 2: Replace hardcoded strings
    content = content.replace('ci.setSrcsystem("DMS");', 'ci.setSrcsystem(SapConstants.SYSTEM_DMS);')
    content = content.replace('ci.setDestsystem("SAP");', 'ci.setDestsystem(SapConstants.SYSTEM_SAP);')

    # Rule 3: Replace status judgment
    content = content.replace(
        '"S".equals(response.getContInfo().getCode()) ? "SUCCESS" : "FAIL"',
        'SapStatusEnum.isSuccess(response.getContInfo().getCode()) ? SapConstants.STATUS_SUCCESS : SapConstants.STATUS_FAIL'
    )

    # Rule 4: Fix catch blocks that lack updateResponse
    catch_pattern = r'catch \(Exception e\) \{\n\s+//\s*\w+Repository\.updateResponse\([^\n]*\);\n\s+throw new RuntimeException\("([^"]+)"'
    # ...etc

    # Rule 5: Ensure trailing newline
    if not content.endswith('\n'):
        content += '\n'

    if content != original:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed: {fname}")
```

**Step D — Compile-check loop**

```bash
# Java / Maven
cd <module-be> && mvn clean compile -DskipTests 2>&1 | tail -30

# Node
npm run build 2>&1 | tail -20

# Python
python -m py_compile $(git diff --name-only | grep '\.py$')
```

If compilation fails:
1. Read the error message and file path
2. Identify the root cause (usually: broken catch blocks from greedy regex, duplicate lines, or missing imports)
3. Fix the specific file with `patch` or `read_file`/`write_file`
4. Re-run compile
5. Repeat until BUILD SUCCESS

**Common compilation errors from bulk regex fixes:**
- **Greedy regex duplicates** — a `.*` matched too much, leaving duplicate `catch` blocks. Fix by tightening the regex or patching the specific file.
- **Missing imports** — new constant references require new imports that the script didn't add.
- **Unclosed strings** — regex replacement accidentally split a string literal across lines.

**Step E — Verify with spot checks**

After compilation succeeds, verify at least 2-3 representative files to ensure the fix was applied correctly:

```bash
grep -A5 "catch (Exception e)" SapSd021ServiceImpl.java
grep "SapConstants" SapFico030ServiceImpl.java | head -5
```

**Step F — Commit strategy**

Stage ONLY the files relevant to the fix. In a mixed working tree (with other uncommitted changes):

```bash
# Stage specific files
git add c-oem-isscp-common-be/.../SapStatusEnum.java
git add c-oem-isscp-common-be/.../*ServiceImpl.java
git add c-oem-isscp-common-scripts/.../01_create_*.sql

# Commit
git commit -m "fix(sap): <summary>

- <change 1>
- <change 2>"
```

Do NOT push unless the user explicitly asks.

### 8.3 Common Cross-File Fix Patterns

| Issue | Regex Approach |
|-------|----------------|
| Inconsistent exception handling | Match `catch (Exception e) {\n\s+(//\s*)?\w+Repository\.updateResponse\(...` |
| Hardcoded strings → constants | Simple `content.replace('"DMS"', 'CONSTANT')` |
| Status logic unification | Replace `"S".equals(code)` with `Enum.isSuccess(code)` |
| Missing imports | `if 'X' in content and 'import ...X' not in content:` then insert |
| Missing newlines at EOF | `if not content.endswith('\n'): content += '\n'` |
| Wrong enum/constant reference | `content.replace('OLD_CONSTANT', 'NEW_CONSTANT')` |

## Pitfalls

- **Commit not found** — might be in a different sub-repo, or the hash is truncated
- **Binary files in diff** — `git show` will show binary patches; skip or use `-- '*.java' '*.sql'` to filter
- **Merge commits** — `git show` on a merge shows all changes from the merged branch; use `-m` flag to see per-parent diff
- **Large commits** — Don't review every file individually if >50 files. Focus on the architectural layers and spot-check patterns.
- **Renamed files** — `git show --stat` shows renames; ensure you're reviewing the new names

## Quick Commands Reference

```bash
# Overview
git show --stat <hash>

# Specific file diff
git show <hash> -- path/to/file.java

# All Java files only
git show <hash> -- '*.java'

# Find most changed files
git show --stat <hash> | sort -t'|' -k2 -rn | head -10

# Search for patterns in the diff
git show <hash> | grep "^+" | grep -i "TODO\|FIXME\|HACK"
git show <hash> | grep "^+" | grep -E "@Transactional|Propagation."
```

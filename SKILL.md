---
name: workbuddy-cross-device-migration
description: "跨设备迁移 WorkBuddy 数据并恢复对话历史的工作流。This skill should be used when a user wants to move WorkBuddy data between two computers (台式机到笔记本 / 国内到海外), restore conversation history on a new machine, fix empty conversation list errors, or fix work directory missing errors after migration. Covers: identifying what must be synced (workbuddy.db sessions table, projects jsonl files, profile), merging session indexes between two machines, fixing workDir paths across different Windows usernames, and avoiding the WAL-overwrite, bat-encoding, and git-protocol pitfalls. 触发词：跨设备、迁移 WorkBuddy、换电脑、恢复对话历史、对话列表为空、工作目录缺失、sync WorkBuddy 数据。"
agent_created: true
---

# 跨设备迁移 WorkBuddy 数据与对话历史恢复

## 目标

把一台电脑（源机）的 WorkBuddy 数据完整迁移到另一台电脑（目标机），
使用户在目标机能看到源机的全部历史对话并可正常点开阅读。

## 使用时机

- 用户换电脑 / 跨设备使用 WorkBuddy，需要保留对话历史
- 目标机对话列表为空（"什么历史都没看到"）
- 点进对话报"工作目录可能已被重命名或删除"
- 两台机器 Windows 用户名不同导致路径错乱

## 数据迁移清单（先读 reference）

执行前先读 `references/workbuddy-storage-layout.md`——里面是存储布局、
核心机制与排查表。简版清单：

| 必须同步 | 说明 |
|---|---|
| `profile/` | MEMORY.md、SOUL/IDENTITY/USER.md、skills/ |
| `wb-data/projects/*.jsonl` | 对话正文 |
| `wb-data/workbuddy.db` | **会话列表数据源（最易漏）** |
| `wb-data/app/sessions.json` | 会话索引 |
| `wb-data/{blobs,artifact-index,edge-sync-mapping.db}` | 附件/工件/映射 |
| `workspace/` | 工作区代码 + .workbuddy/memory |

## 标准流程

### 阶段 1：源机打包 → 传输

1. 源机收集上述清单数据，打成 zip（含 .git 历史更佳，方便目标机直接 pull）。
2. 传输方式按网络环境：
   - 跨国内/海外且 GitHub 不稳 → ToDesk 文件传输 / 网盘
   - GitHub 可达 → clone/pull 私有仓库
3. 目标机解压，记录解压路径。

### 阶段 2：目标机恢复基础数据

```bash
# profile + wb-data 拷入用户目录
robocopy REPO\profile  %USERPROFILE%\.workbuddy  /E
robocopy REPO\wb-data  %USERPROFILE%\.workbuddy  /E
# workspace 拷入工作区目录
robocopy REPO\workspace  %USERPROFILE%\WorkBuddy\WORKSPACE_DIR  /E
```

### 阶段 3：合并会话列表（两台机器各有会话时）

目标机 WorkBuddy 已产生本地会话时，直接覆盖会丢本地会话。用合并脚本：

```bash
python scripts/merge_workbuddy_db.py \
  SOURCE_DB TARGET_DB --out %USERPROFILE%\.workbuddy\workbuddy.db.merged
```

合并后验证：`SELECT COUNT(*) FROM sessions` 应为两机并集（按 id 去重）。

### 阶段 4：修正 workDir 路径（用户名不同时）

源机会话的 cwd 指向 `C:\Users\OLD_USERNAME\...`，目标机无此路径 →
点开报"工作目录已被重命名或删除"。执行：

```bash
python scripts/fix_workdirs.py %USERPROFILE%\.workbuddy\workbuddy.db.merged \
  --old-user OLD_USERNAME --new-user NEW_USERNAME
```

该脚本：① db 中 cwd 替换用户名 ② 创建对应工作区目录 ③ projects 目录同步改名
（`c-Users-OLD-*` → `c-Users-NEW-*`，否则正文匹配不上）。

### 阶段 5：替换 db（关键安全步骤）

**WorkBuddy 运行中改 workbuddy.db 会被 WAL 回写覆盖（实测 13→4 条）。**

1. 完全退出 WorkBuddy（窗口 + 托盘图标右键退出）。
2. 备份：`copy %USERPROFILE%\.workbuddy\workbuddy.db workbuddy.db.bak`
3. 替换：`copy workbuddy.db.merged workbuddy.db`
4. 删除缓存：`del workbuddy.db-wal workbuddy.db-shm`（如有）
5. 重开 WorkBuddy → 验证对话列表。

> 若交付给用户手动执行：提供**纯英文 ASCII** 的 .bat（中文会 GBK 乱码）。

### 阶段 6：验证

```sql
-- 检查 sessions 表
SELECT id, cwd, title FROM sessions WHERE deleted_at IS NULL;
-- 确认 cwd 目录存在、projects 目录名与 cwd 对应、jsonl 文件在
```

## 常见坑速记

- 对话列表数据源是 `workbuddy.db` 的 sessions 表，不是 sessions.json。
- projects 目录名由 cwd 生成，改 cwd 必须同步改名 projects。
- workDir 必须真实存在。
- db 替换必须退出 WorkBuddy（WAL 覆盖）。
- .bat 用纯 ASCII。
- git 协议 v2 静默失败 → `-c protocol.version=1` 或 zipball 下载。

## 交付物

- 合并/修复后的 `workbuddy.db`
- 需要的脚本：`scripts/merge_workbuddy_db.py`、`scripts/fix_workdirs.py`
- 用户操作说明（退出 WorkBuddy → 跑脚本/命令 → 重开）

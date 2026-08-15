# WorkBuddy 跨设备迁移指南 / WorkBuddy Cross-Device Migration Guide

> 把一台电脑上的 WorkBuddy（对话历史 + 记忆 + 技能 + 工作区）完整迁移到另一台电脑，
> 避免"对话列表为空"、"工作目录缺失"等坑。
> Migrate WorkBuddy data (conversation history, memory, skills, workspaces) between
> two computers without hitting the "empty conversation list" or "missing work directory" traps.

---

## 背景 / Background

WorkBuddy 的数据分散存储在 `~/.workbuddy/` 多个子目录中。很多人以为整个文件夹拷过去就行，
但实际上：

- **对话列表的索引**在 `workbuddy.db` 的 `sessions` 表（最容易被漏掉）
- **对话正文**在 `projects/*.jsonl`（按会话一个文件）
- **工作目录（workDir）** 记录在 db 里，且 **`projects/` 目录名由 workDir 生成**

漏拷任何一个，就会出现"对话列表为空"或"点进对话报工作目录缺失"。

## 常见问题 / Common Problems

| 症状 | 原因 |
|---|---|
| 对话列表为空 | 漏了 `workbuddy.db`（会话列表数据源） |
| 列表有、点开为空 | 漏了 `projects/*.jsonl`（对话正文） |
| 点开报"工作目录已被重命名或删除" | `sessions.cwd` 指向目标机不存在的路径（如两台电脑 Windows 用户名不同） |
| 合并后重启又变少 | WorkBuddy 运行中改 db 被 WAL 机制回写覆盖 |

## 快速上手 / Quick Start

### 0. 准备 / Prerequisites

- Windows 电脑两台（源机 + 目标机）
- Python 3（目标机，用于跑合并脚本）
- 迁移介质：U 盘 / 网盘 / ToDesk 文件传输 / GitHub 私有仓库

### 1. 源机打包 / Package on source machine

在**源机**上，把以下内容打包成 zip：

```
profile/                          # MEMORY.md、SOUL.md、IDENTITY.md、USER.md、skills/
wb-data/projects/                 # 对话正文（*.jsonl）★ 必带
wb-data/workbuddy.db              # 会话列表数据源 ★ 必带（最易漏）
wb-data/app/sessions.json         # 会话索引
wb-data/{blobs,artifact-index,edge-sync-mapping.db}  # 附件/工件/映射
workspace/                        # 工作区代码 + .workbuddy/memory
```

> 完整清单见 `references/workbuddy-storage-layout.md`（含"哪些是运行时缓存、勿拷"）。

### 2. 传输 / Transfer

按网络环境选择：U 盘、网盘、ToDesk 文件传输，或 GitHub 私有仓库 clone/pull。

### 3. 目标机恢复基础数据 / Restore on target machine

```bash
robocopy <解压目录>\profile  %USERPROFILE%\.workbuddy  /E
robocopy <解压目录>\wb-data  %USERPROFILE%\.workbuddy  /E
robocopy <解压目录>\workspace  %USERPROFILE%\WorkBuddy\<工作区名>  /E
```

### 4. 合并会话列表（可选，两台电脑各有会话时）/ Merge session lists

```bash
python scripts/merge_workbuddy_db.py ^
  <源机db> %USERPROFILE%\.workbuddy\workbuddy.db --out %USERPROFILE%\.workbuddy\workbuddy.db.merged
```

### 5. 修正工作目录路径 / Fix workDir paths

两台电脑 Windows 用户名不同（如 `OLD_USERNAME` vs `NEW_USERNAME`）时，会话的
workDir 会指向源机路径。执行：

```bash
python scripts/fix_workdirs.py %USERPROFILE%\.workbuddy\workbuddy.db.merged ^
  --old-user OLD_USERNAME --new-user NEW_USERNAME
```

该脚本自动完成三件事：
1. 修正 db 中所有会话的 `cwd` 路径
2. 创建对应的工作区目录
3. **同步重命名 `projects/` 目录**（目录名由 workDir 生成，不改则正文加载失败）

### 6. 替换数据库 / Replace the database（关键安全步骤）

> ⚠️ **WorkBuddy 运行中修改 `workbuddy.db` 会被 WAL 机制回写覆盖！**

1. **完全退出 WorkBuddy**（窗口 + 托盘图标右键退出）
2. 备份：`copy %USERPROFILE%\.workbuddy\workbuddy.db workbuddy.db.bak`
3. 替换：`copy workbuddy.db.merged workbuddy.db`
4. 删除缓存：`del workbuddy.db-wal workbuddy.db-shm`（如有）
5. 重新打开 WorkBuddy → 验证对话列表

### 7. 验证 / Verify

```sql
SELECT id, cwd, title FROM sessions WHERE deleted_at IS NULL;
-- 确认 cwd 目录存在、projects 目录名与 cwd 对应、jsonl 文件在
```

## 文件说明 / Files

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 技能定义（供 WorkBuddy 自动调用） |
| `scripts/merge_workbuddy_db.py` | 合并两台设备的会话列表 |
| `scripts/fix_workdirs.py` | 修正 workDir 路径 + 同步重命名 projects 目录 |
| `references/workbuddy-storage-layout.md` | 存储布局详解 + 排查速查表 |

## 常见坑 / Pitfalls

- **对话列表数据源是 `workbuddy.db` 的 sessions 表**，不是 `sessions.json`
- **`projects/` 目录名由 workDir 生成**，改 cwd 必须同步改名目录
- **workDir 必须真实存在**，否则点进对话报"工作目录缺失"
- **db 替换必须退出 WorkBuddy**（WAL 覆盖）
- **.bat 脚本含中文会 GBK 乱码**，如交付 .bat 请用纯英文 ASCII
- **git 协议 v2 静默失败**（海外直连时偶发）：用 `git -c protocol.version=1` 或 zipball 下载绕过

## License

MIT

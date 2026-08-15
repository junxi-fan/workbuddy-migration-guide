# WorkBuddy 本地数据存储布局（Windows）

> 迁移 WorkBuddy 数据前必读。数据分散在 `~/.workbuddy/` 多个子目录，
> 只拷一部分会导致"对话列表为空"或"点进对话报工作目录缺失"。

## 关键文件一览

| 路径（`~/.workbuddy/` 下） | 作用 | 迁移必须 |
|---|---|---|
| `MEMORY.md`、`SOUL.md`、`IDENTITY.md`、`USER.md` | 用户画像、身份文件 | ✅ |
| `skills/` | 用户级技能 | ✅ |
| `projects/<workdir-hash>/<conversationId>.jsonl` | **对话正文**（每会话一个文件，含子代理） | ✅ 漏了 = 有列表但点开空 |
| `workbuddy.db` | **会话列表数据源**（`sessions` 表 = 对话列表；含 `automations` 表） | ✅ **漏了 = 对话列表为空**（最易漏） |
| `app/sessions.json` | 会话索引（conversationId→工作区） | ✅ 建议带 |
| `edge-sync-mapping.db*` | 边缘同步映射 | 建议带 |
| `blobs/` | 附件/图片 | 建议带 |
| `artifact-index/` | 工件索引（任务、文件变更） | 建议带 |
| `audit-log/` | 命令审计日志（非对话） | 可选 |
| `file-history/` | 文件历史版本 | 可选 |
| `app/session/Local Storage/leveldb` | 渲染进程 localStorage | 可选（不含对话列表） |
| `sessions/`、`app/session/` | 运行时进程信息/Electron 缓存 | ❌ 勿拷 |

## 核心机制（决定成败的 3 条）

1. **对话列表 = `workbuddy.db` 的 `sessions` 表**
   - 判断依据：WorkBuddy 启动日志 `[SessionStore] read done ... conversations:N`，N 就是列表条数。
   - `app/sessions.json` 会被 WorkBuddy 按 db 内容重写，改它没用。
   - 只恢复 `projects/*.jsonl`（正文）而没有 `workbuddy.db` → 列表仍为空。

2. **`projects/` 目录名由 workDir 生成**
   - 规则：`C:\Users\foo\WorkBuddy\2026-08-06` → `c-Users-foo-WorkBuddy-2026-08-06`
   - 若改 db 中 `sessions.cwd`（如 OLD_USERNAME→NEW_USERNAME），**必须同步重命名 projects 目录**，否则正文匹配不上（jsonl 文件名 = conversationId）。

3. **workDir 必须真实存在**
   - 点进会话报"工作目录可能已被重命名或删除" = sessions.cwd 指向的目录在当前机器不存在。
   - 迁移后需创建对应工作区目录（或改用本机真实路径）。

## 危险操作

- **WorkBuddy 运行中改 `workbuddy.db` 会被 WAL 回写覆盖**（实测合并 13 条后重启变回 4 条）。
  → 所有 db 替换操作必须：完全退出 WorkBuddy（含托盘）→ 改 → 重开。
- **`.bat` 脚本含中文会按 GBK 解析乱码**（报"`'xx' 不是内部或外部命令`"）。
  → bat 一律纯英文 ASCII；中文内容用 Python/PS1 或 UTF-8 注意编码。

## 网络坑（中国大陆 ↔ 海外直连）

| 场景 | 现象 | 处理 |
|---|---|---|
| 海外直连 GitHub 网页 | OK（curl 200） | 无需代理 |
| git 协议 v2（fetch/push） | 静默失败，exit 1 无输出 | `git -c protocol.version=1 fetch/push` |
| git 仍失败 | 间歇性 | 重试 3-6 次；或 `curl -H "Authorization: token <PAT>" https://api.github.com/repos/<user>/<repo>/zipball/main` 下载 zip 绕过 |
| 中国大陆访问 GitHub | 必须走代理（如本机 HTTP 代理，代理间歇失效） | 重试；push 后清除 remote URL 中 token |

## 排查速查表

| 症状 | 原因 | 处理 |
|---|---|---|
| 对话列表空 | `workbuddy.db` 没恢复 | 恢复 db 或合并 sessions 表 |
| 列表有、点开空 | `projects/*.jsonl` 没恢复 | 恢复 projects 目录 |
| 点开报工作目录缺失 | `sessions.cwd` 指向不存在的路径 | fix_workdirs.py 修正 + 建目录 |
| 列表只有本机几个 | db 未合并另一台设备的会话 | merge_workbuddy_db.py 合并 |
| 合并后重启又变少 | WorkBuddy 运行中改 db 被 WAL 覆盖 | 完全退出后替换 |
| bat 报 `'13' 不是内部或外部命令` | bat 含中文/编码问题 | 改纯英文 ASCII |

#!/usr/bin/env python3
"""合并两台设备的 WorkBuddy workbuddy.db（会话列表数据源）。

用法:
  python merge_workbuddy_db.py <source_db> <local_db> [--out <output_db>]

说明:
- source_db: 主设备（如台式机）的 workbuddy.db，包含大部分会话
- local_db:  当前设备（如笔记本）的 workbuddy.db，可能含本地独有会话
- 合并规则: 以 source_db 为基础，把 local_db 中 cwd 属于本机
  （不含另一设备用户名）且 id 未存在的会话补入
- 输出: source_db + 补入的本地会话（默认 <source_db>.merged）

注意: 两台设备 Windows 用户名可能不同（如 OLD_USERNAME vs NEW_USERNAME），
本地会话判定用 cwd 中是否含 local_db 所在机器的用户名路径。
"""
import sqlite3
import shutil
import sys
import os


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    src_db = sys.argv[1]
    local_db = sys.argv[2]
    out_db = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == '--out' else src_db + '.merged'

    shutil.copy2(src_db, out_db)

    src = sqlite3.connect(src_db)
    local = sqlite3.connect(local_db)
    out = sqlite3.connect(out_db)
    src_cur, local_cur, out_cur = src.cursor(), local.cursor(), out.cursor()

    existing = {r[0] for r in out_cur.execute('SELECT id FROM sessions')}
    print("source sessions:", len(existing))

    cols = [c[1] for c in out_cur.execute('PRAGMA table_info(sessions)')]
    local_cols = [c[1] for c in local_cur.execute('PRAGMA table_info(sessions)')]

    # 判定"本地会话": cwd 不含 source 机器用户名（如 OLD_USERNAME）
    src_username = None
    for row in src_cur.execute("SELECT cwd FROM sessions LIMIT 200").fetchall():
        if row[0] and 'Users' in row[0]:
            parts = row[0].replace('\\', '/').split('/Users/')
            if len(parts) > 1:
                src_username = parts[1].split('/')[0]
                break
    print("source machine username:", src_username)

    added = 0
    for row in local_cur.execute("SELECT * FROM sessions").fetchall():
        d = dict(zip(local_cols, row))
        if d['id'] in existing:
            continue
        cwd = d.get('cwd') or ''
        # 若 cwd 属于 source 机器用户名则跳过（避免反向混入）
        if src_username and ('/Users/' + src_username + '/' in cwd.replace('\\', '/') or
                             '\\Users\\' + src_username + '\\' in cwd):
            continue
        placeholders = ','.join('?' * len(cols))
        vals = [d.get(c) for c in cols]
        out_cur.execute(f'INSERT INTO sessions ({",".join(cols)}) VALUES ({placeholders})', vals)
        added += 1
        print("  +", d['id'][:8], d.get('title') or '(no title)')

    out.commit()
    total = out_cur.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
    print(f"merged: +{added}, total {total}")
    out.close(); local.close(); src.close()


if __name__ == '__main__':
    main()

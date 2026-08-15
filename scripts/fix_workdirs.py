#!/usr/bin/env python3
"""修复迁移后的会话工作目录（workDir）并同步重命名 projects 目录。

背景: 源机的会话 workDir 指向 C:\\Users\\OLD_USERNAME\\...，
目标机上是 C:\\Users\\NEW_USERNAME\\...。若直接使用，点进会话会报
"工作目录可能已被重命名或删除"，且 projects 目录名（由 workDir
生成）与 db 中 cwd 不匹配导致正文加载失败。

用法:
  python fix_workdirs.py <db_path> --old-user OLD_USERNAME --new-user NEW_USERNAME
  python fix_workdirs.py <db_path> --old-user OLD_USERNAME --new-user NEW_USERNAME --no-rename

行为:
1. 把 sessions.cwd 中 --old-user 替换为 --new-user
2. 创建新 workDir 对应的目录（若不存在；目录在 %USERPROFILE% 下按 WorkBuddy 惯例）
3. 把 ~/.workbuddy/projects/ 下 c-Users-OLD-* 目录重命名为 c-Users-NEW-*

注意: 需在 WorkBuddy 完全退出后执行（运行中改 db 会被 WAL 回写覆盖）。
"""
import sqlite3
import os
import sys
import shutil


def main():
    args = sys.argv[1:]
    if len(args) < 2 or '--old-user' not in args or '--new-user' not in args:
        print(__doc__)
        sys.exit(1)

    db_path = args[0]
    old_user = args[args.index('--old-user') + 1]
    new_user = args[args.index('--new-user') + 1]
    do_rename = '--no-rename' not in args

    home = os.path.expanduser('~')
    projects_root = os.path.join(home, '.workbuddy', 'projects')

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    old_prefix = 'C:\\Users\\' + old_user
    rows = cur.execute("SELECT id, cwd FROM sessions").fetchall()
    changed = 0
    for sid, cwd in rows:
        if cwd and old_prefix in cwd:
            new_cwd = cwd.replace(old_prefix, 'C:\\Users\\' + new_user)
            cur.execute('UPDATE sessions SET cwd = ? WHERE id = ?', (new_cwd, sid))
            changed += 1
            # 创建新 workDir 目录（WorkBuddy 要求存在）
            os.makedirs(new_cwd, exist_ok=True)
            print(f"  {sid[:8]}: {new_cwd}")
    con.commit()

    # 重命名 projects 目录: c-Users-<old>-* -> c-Users-<new>-*
    if do_rename and os.path.isdir(projects_root):
        renamed = 0
        for d in os.listdir(projects_root):
            prefix = 'c-Users-' + old_user + '-'
            if d.startswith(prefix):
                new_name = 'c-Users-' + new_user + '-' + d[len(prefix):]
                src = os.path.join(projects_root, d)
                dst = os.path.join(projects_root, new_name)
                if not os.path.exists(dst):
                    os.rename(src, dst)
                    renamed += 1
                    print(f"  rename projects: {d} -> {new_name}")
        print(f"renamed projects dirs: {renamed}")

    print(f"fixed workdirs: {changed}")
    con.close()


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
r"""把《Chill with You: Lo-Fi Story》日历里的日记导出成 txt。

原理
----
游戏用 Easy Save 3 存盘，.es3 文件其实是 gzip 压缩过的 JSON 变体
（数字 key 没加引号，如 `"DiaryList" : {1:{...}}`）。
解压后日记正文位于 `DiaryList[日].DiaryText`，是 UTF-8 中文。
本脚本直接读存档，不需要进游戏、不需要 mod、不需要 BepInEx。

用法
----
    直接运行（自动探测存档目录）:
        python export_diaries.py
    手动指定存档目录（Steam 用户目录，其下是若干数字文件夹）:
        python export_diaries.py --save-dir "D:\...\SaveData\Release\v2"
    手动指定输出目录:
        python export_diaries.py --out-dir "D:\我的日记"

打包成 exe 后双击即可；导出的文件在 exe 同目录的「日记导出」文件夹。
建议导出前先退出游戏，让当天新写的日记落盘。
"""
import sys
import os
import gzip
import json
import glob
import re
import argparse
from datetime import date

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

APP_REL = os.path.join('nestopi', 'Chill With You', 'SaveData', 'Release', 'v2')
WEEK = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
VALID_ESC = set('"\\/bfnrtu')


def base_dir():
    """exe 用所在目录，源码用脚本所在目录。"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def default_roots():
    """自动探测常见存档根目录（LocalLow 下按游戏公司/游戏名）。"""
    candidates = []
    home = os.path.expanduser('~')
    local = os.environ.get('LOCALAPPDATA', '')
    if local:
        candidates.append(os.path.join(local, 'Low', APP_REL))
    candidates.append(os.path.join(home, 'AppData', 'LocalLow', APP_REL))
    seen, out = set(), []
    for p in candidates:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


def es3_to_json(text):
    """把 ES3 的 JSON 变体规范化成标准 JSON。

    1) 给裸数字 key 加引号：{1:{...}} -> {"1":{...}}
    2) 修复游戏文本里的非法反斜杠转义（如 \\“ -> “），
       合法转义（\\n \\" 等）原样保留。
    """
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == '\\':
                if i + 1 < n and text[i + 1] in VALID_ESC:
                    out.append('\\')
                    out.append(text[i + 1])
                    i += 2
                else:
                    out.append('\\\\')
                    i += 1
            elif c == '"':
                in_str = False
                out.append(c)
                i += 1
            else:
                out.append(c)
                i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif c.isdigit() or (c == '-' and i + 1 < n and text[i + 1].isdigit()):
            j = i
            while j < n and (text[j].isdigit() or text[j] in '-.'):
                j += 1
            k = j
            while k < n and text[k] in ' \t\r\n':
                k += 1
            if k < n and text[k] == ':':
                out.append('"' + text[i:j] + '"')
                i = j
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def clean(t):
    """统一换行并清掉残留的反斜杠转义。"""
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    t = t.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n')
    t = re.sub(r'\\(.)', r'\1', t)
    return t.strip()


def collect(roots):
    """返回 {(年,月,日): (正文, 来源文件名)}。"""
    entries = {}
    files = []
    for root in roots:
        if os.path.isfile(root):
            files.append(root)
        elif os.path.isdir(root):
            files.extend(sorted(glob.glob(os.path.join(root, '*.es3'))))
            # 兼容直接指向数字子目录的上一层：再往里找一层
            for sub in glob.glob(os.path.join(root, '*')):
                if os.path.isdir(sub):
                    files.extend(sorted(glob.glob(os.path.join(sub, '*.es3'))))
    seen = set()
    for p in files:
        ap = os.path.abspath(p)
        if ap in seen:
            continue
        seen.add(ap)
        try:
            dec = gzip.decompress(open(p, 'rb').read()).decode('utf-8', errors='replace')
        except Exception:
            continue
        if 'CalenderMonthlyData' not in dec:  # 游戏把 Calendar 拼成了 Calender
            continue
        fn = os.path.basename(p)
        try:
            data = json.loads(es3_to_json(dec))
        except Exception as e:
            print('  [跳过] %s 解析失败: %s' % (fn, e))
            continue
        cnt = 0
        for _sid, entry in data.items():
            if not isinstance(entry, dict) or 'value' not in entry:
                continue
            v = entry['value']
            if not isinstance(v, dict) or 'DiaryList' not in v:
                continue
            y, m = v.get('Year'), v.get('Month')
            if not y or not m:
                continue
            for d, rec in v['DiaryList'].items():
                if not isinstance(rec, dict):
                    continue
                txt = clean(str(rec.get('DiaryText', '')))
                if txt:
                    entries[(int(y), int(m), int(d))] = (txt, fn)
                    cnt += 1
        if cnt:
            print('  %-32s 提取 %d 篇' % (fn, cnt))
    return entries


def write_out(entries, out_dir):
    daily_dir = os.path.join(out_dir, 'daily')
    os.makedirs(daily_dir, exist_ok=True)
    keys = sorted(entries.keys())

    summary = ['《Chill with You: Lo-Fi Story》日历日记全集',
               '共 %d 篇（按日期排序）\n' % len(keys)]
    for (y, m, d) in keys:
        txt = entries[(y, m, d)][0]
        try:
            wd = WEEK[date(y, m, d).weekday()]
        except Exception:
            wd = ''
        summary += ['=' * 46, '%04d-%02d-%02d %s' % (y, m, d, wd), '=' * 46, txt, '']

    all_path = os.path.join(out_dir, '日记全集.txt')
    with open(all_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary))

    for (y, m, d) in keys:
        txt = entries[(y, m, d)][0]
        day_path = os.path.join(daily_dir, '%04d-%02d-%02d.txt' % (y, m, d))
        with open(day_path, 'w', encoding='utf-8') as f:
            f.write('%04d-%02d-%02d\n\n%s\n' % (y, m, d, txt))
    return all_path, daily_dir


def interactive_menu(args):
    """双击 exe（无命令行参数）时进入的交互菜单。"""
    while True:
        print()
        print('=' * 46)
        print(' Chill with You 日记导出器')
        print('=' * 46)
        print(' [1] 一键导出所有日记')
        print(' [2] 仅导出某一天日记（直接回车 = 今天）')
        print(' [0] 退出')
        choice = input('请选择：').strip()
        if choice == '0':
            return
        if choice == '1':
            run_export(args)
            return
        if choice == '2':
            today = date.today()
            default = '%04d%02d%02d' % (today.year, today.month, today.day)
            s = input('输入日期（如 20260103，回车 = 今天 %s）：' % default).strip()
            target = parse_date_input(s) if s else today
            if target is None:
                print('  日期格式不对，请输入 8 位数字，如 20260103')
                continue
            run_export(args, only_day=target)
            return
        print('  请输入 0 / 1 / 2')


def parse_date_input(s):
    """把 20260103 / 2026-01-03 / 2026.1.3 解析成 date，失败返回 None。"""
    s = s.strip().replace('-', '').replace('/', '').replace('.', '')
    if not s.isdigit() or len(s) != 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def run_export(args, only_day=None):
    """扫描存档并导出。only_day 不为 None 时只导出那一天。"""
    ap = argparse.ArgumentParser(description='导出 Chill with You: Lo-Fi Story 的日历日记为 txt')
    ap.add_argument('--save-dir', action='append', metavar='DIR',
                    help='存档目录（可重复指定）。默认是自动探测；也可直接指向某个 .es3 文件')
    ap.add_argument('--out-dir', metavar='DIR',
                    help='输出目录，默认在脚本/exe 同目录的「日记导出」')
    args = ap.parse_args()

    roots = args.save_dir if args.save_dir else default_roots()
    roots = [os.path.expanduser(p) for p in roots]
    found = [r for r in roots if os.path.exists(r)]
    if not found:
        print('没找到存档目录，试过的路径：')
        for r in roots:
            print('  ' + r)
        print('请用 --save-dir 手动指定，例如：')
        print('  --save-dir "C:\\Users\\你的用户名\\AppData\\LocalLow\\nestopi\\Chill With You\\SaveData\\Release\\v2"')
        if getattr(sys, 'frozen', False):
            input('\n按回车退出...')
        return

    out_dir = args.out_dir or os.path.join(base_dir(), '日记导出')
    out_dir = os.path.expanduser(out_dir)

    print('扫描存档位置：')
    for r in found:
        print('  ' + r)
    entries = collect(found)
    if not entries:
        print('\n没找到非空日记。（是不是还没在日历里写过？或导出前没退出游戏？）')
        if getattr(sys, 'frozen', False):
            input('\n按回车退出...')
        return

    if only_day is not None:
        day_key = (only_day.year, only_day.month, only_day.day)
        if day_key not in entries:
            print('\n这一天（%04d-%02d-%02d）没有写过日记。' % day_key)
            if getattr(sys, 'frozen', False):
                input('\n按回车退出...')
            return
        txt, _fn = entries[day_key]
        daily_dir = os.path.join(out_dir, 'daily')
        os.makedirs(daily_dir, exist_ok=True)
        try:
            wd = WEEK[only_day.weekday()]
        except Exception:
            wd = ''
        day_path = os.path.join(daily_dir, '%04d-%02d-%02d.txt' % day_key)
        with open(day_path, 'w', encoding='utf-8') as f:
            f.write('%04d-%02d-%02d %s\n\n%s\n' % (day_key[0], day_key[1],
                                                   day_key[2], wd, txt))
        print('\n完成！导出 1 篇：' + day_path)
        if getattr(sys, 'frozen', False):
            input('\n按回车退出...')
        return

    all_path, daily_dir = write_out(entries, out_dir)
    keys = sorted(entries.keys())
    print('\n完成！共 %d 篇，日期范围 %04d-%02d-%02d ~ %04d-%02d-%02d' %
          (len(entries), keys[0][0], keys[0][1], keys[0][2],
           keys[-1][0], keys[-1][1], keys[-1][2]))
    print('汇总文件：' + all_path)
    print('每日文件：' + daily_dir)
    if getattr(sys, 'frozen', False):
        input('\n按回车退出...')


def main():
    ap = argparse.ArgumentParser(description='导出 Chill with You: Lo-Fi Story 的日历日记为 txt')
    ap.add_argument('--save-dir', action='append', metavar='DIR',
                    help='存档目录（可重复指定）。默认是自动探测；也可直接指向某个 .es3 文件')
    ap.add_argument('--out-dir', metavar='DIR',
                    help='输出目录，默认在脚本/exe 同目录的「日记导出」')
    args = ap.parse_args()

    # 双击 exe（无任何命令行参数）时进交互菜单；带参数则保持命令行行为
    if getattr(sys, 'frozen', False) and len(sys.argv) == 1:
        interactive_menu(args)
        return

    run_export(args)


if __name__ == '__main__':
    main()

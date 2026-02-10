
"""
Script Manager 
作者: (Yuan Xinming)
本项目为个人管理脚本所用，现已开源。
欢迎随意 fork 或修改。主要用于本地索引、归档与全局调用。
"""


import sys
import os
import json
import subprocess
import argparse
import shutil
from pathlib import Path

# === 配置区域 ===
BASE_DIR = Path(__file__).parent.resolve()
DATA_FILE = BASE_DIR / "data.json"
STORAGE_DIR = BASE_DIR / "storage"

if not STORAGE_DIR.exists():
    STORAGE_DIR.mkdir()

# === 数据库操作 ===
def load_data():
    if not DATA_FILE.exists():
        return {"scripts": {}, "categories": {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {"scripts": {}, "categories": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# === 核心运行逻辑 ===
def run_script_direct(alias, extra_args):
    data = load_data()
    info = data["scripts"][alias]
    script_path = Path(info["path"])
    
    if script_path.exists():
        cmd = [sys.executable, str(script_path)] + extra_args
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"运行出错: {e}")
    else:
        print(f"错误: 原文件丢失 -> {script_path}")
        if "backup" in info:
            print(f"提示: 备份文件位于 -> {info['backup']}")

# === 管理功能实现 ===
def cmd_list():
    data = load_data()
    scripts = data["scripts"]
    categories = data["categories"]

    if not scripts:
        print("暂无记录。请使用 -add 添加脚本。")
        return

    # 按分类路径排序，确保树状显示的顺序正确
    sorted_items = sorted(scripts.items(), key=lambda x: x[1].get('category', ''))

    print("\n" + "="*80)
    print(f"{'SCRIPT MANAGER (TREE VIEW)':^80}")
    print("="*80)

    last_cat = None
    for alias, info in sorted_items:
        cat = info.get("category", "未分类")
        
        # 当分类发生变化时，打印分类标题
        if cat != last_cat:
            # 计算缩进深度 (按 / 分隔)
            depth = cat.count('/')
            indent = "  " * depth
            cat_name = cat.split('/')[-1]
            cat_note = categories.get(cat, "")
            
            print(f"\n{indent}📂 {cat_name} " + (f"({cat_note})" if cat_note else ""))
            print(f"{indent}{'-' * (80 - len(indent))}")
            last_cat = cat

        # 打印脚本，根据分类深度缩进
        depth = cat.count('/')
        indent = "  " * (depth + 1)
        print(f"{indent}* {alias:<15} : {info.get('note', '')}")
    print("\n")

def cmd_add_script(args):
    category = args.category.replace('\\', '/') # 统一使用 / 作为分隔符
    src_path = Path(args.file).resolve()
    note = args.note

    if not src_path.exists():
        print(f"错误: 找不到文件 '{src_path}'")
        return

    # 1. 物理归档：支持多级子目录
    cat_parts = category.split('/')
    cat_dir = STORAGE_DIR.joinpath(*cat_parts)
    if not cat_dir.exists():
        cat_dir.mkdir(parents=True)

    backup_path = cat_dir / src_path.name
    try:
        shutil.copy2(src_path, backup_path)
    except Exception as e:
        print(f"归档失败: {e}")
        return

    # 2. 数据库更新
    alias = src_path.stem
    data = load_data()
    
    original_alias = alias
    counter = 1
    while alias in data["scripts"]:
        # 如果路径相同，视为覆盖更新
        if data["scripts"][alias].get("path") == str(src_path): break
        alias = f"{original_alias}_{counter}"
        counter += 1

    data["scripts"][alias] = {
        "path": str(src_path),
        "backup": str(backup_path),
        "category": category,
        "note": note
    }

    if category not in data["categories"]:
        data["categories"][category] = ""

    save_data(data)
    print(f"成功添加并归档至 {category}: {alias}")

def cmd_add_category(args):
    data = load_data()
    cat = args.name.replace('\\', '/')
    data["categories"][cat] = args.note
    save_data(data)
    print(f"分类 '{cat}' 备注已更新。")

def cmd_update_note(args):
    data = load_data()
    if args.alias not in data["scripts"]:
        print(f"错误: 找不到脚本 '{args.alias}'")
        return
    data["scripts"][args.alias]["note"] = args.note
    save_data(data)
    print(f"备注已更新。")

def main():
    data = load_data()
    
    # 优先级 1: 脚本运行拦截
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        target_alias = first_arg
        
        # 容错：去掉前面的横杠
        if target_alias not in data["scripts"] and target_alias.startswith("-"):
            if target_alias not in ["-add", "-l", "-cat", "-n", "-h", "--help"]:
                stripped = target_alias.lstrip("-")
                if stripped in data["scripts"]:
                    target_alias = stripped

        if target_alias in data["scripts"]:
            run_script_direct(target_alias, sys.argv[2:])
            return

    # 优先级 2: 管理命令解析
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("-l", "--list", action="store_true")
    parser.add_argument("-add", nargs=3)
    parser.add_argument("-cat", nargs=2)
    parser.add_argument("-n", nargs=2)

    args, unknown = parser.parse_known_args()

    if args.help or len(sys.argv) == 1:
        print("\n=== 脚本管理系统 (多级分类归档) ===")
        print("1. 运行: s <脚本名> [参数...] (支持 -h)")
        print("2. 列表: s -l")
        print("3. 添加: s -add <分类/子类> <文件> <备注>")
        print("4. 分类备注: s -cat <分类/子类> <备注>")
        print("5. 修改备注: s -n <脚本名> <新备注>")
        return

    if args.list:
        cmd_list()
    elif args.add:
        ns = argparse.Namespace(category=args.add[0], file=args.add[1], note=args.add[2])
        cmd_add_script(ns)
    elif args.cat:
        ns = argparse.Namespace(name=args.cat[0], note=args.cat[1])
        cmd_add_category(ns)
    elif args.n:
        ns = argparse.Namespace(alias=args.n[0], note=args.n[1])
        cmd_update_note(ns)
    else:
        print(f"错误: 未知指令 '{sys.argv[1]}'")

if __name__ == "__main__":
    main()
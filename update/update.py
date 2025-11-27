import subprocess
import requests
import tkinter as tk
from tkinter import messagebox, font
import os

def get_local_git_tag(repo_dir="."):
    """获取本地 Git 仓库的当前 Tag"""
    try:
        result = subprocess.run(
            ["git", "-C", repo_dir, "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None  # 可能不是 Git 仓库，或者没有 Tag

def get_latest_release_tag(owner, repo):
    """获取 GitHub 最新 Release 的 Tag"""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["tag_name"]
    else:
        raise Exception(f"Failed to fetch release info (HTTP {response.status_code})")

def execute_update_script(script_path):
    """执行更新脚本"""
    try:
        # 添加执行权限（仅限 Unix-like 系统）
        if os.name != 'nt':  # 非 Windows 系统
            subprocess.run(["chmod", "+x", script_path], check=True)
        
        # 执行脚本
        subprocess.run(["bash", script_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"执行更新脚本失败: {e}")
        return False

def show_update_notification(local_tag, remote_tag, script_path):
    """显示更新通知弹窗，并在确认后执行脚本"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 弹窗内容
    title = "版本更新提示"
    message = f"""检测到 新版本可用！

    当前本地版本: {local_tag}

    最新发布版本: {remote_tag}

    请暂停数据采集，

    点击"确定" 
    
    将自动执行更新脚本:{script_path}
    """
    
    # 显示确认弹窗
    result = messagebox.askyesno(title, message)
    
    if result:  # 用户点击"是"
        print("用户确认更新，正在执行脚本...")
        if execute_update_script(script_path):
            messagebox.showinfo("成功", "更新脚本执行完成！")
        else:
            messagebox.showerror("错误", "更新脚本执行失败，请手动更新")

# 示例：比较本地和远程版本
owner = "FlagOpen"
repo = "RoboDriver-Server"
update_script = "update.sh"  # 你的更新脚本路径

try:
    local_tag = get_local_git_tag()  # 本地 Tag
    remote_tag = get_latest_release_tag(owner, repo)  # 远程 Release Tag

    print(f"Local Git Tag: {local_tag}")
    print(f"Latest Release Tag: {remote_tag}")

    if local_tag == remote_tag:
        print("✅ 本地代码与最新 Release 版本一致")
    else:
        print("❌ 本地代码与最新 Release 版本不一致")
        show_update_notification(local_tag, remote_tag, update_script)  # 显示弹窗

except Exception as e:
    print(f"检查版本时出错: {e}")
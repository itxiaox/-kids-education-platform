#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
代码同步工具 - 先从GitHub拉取最新代码，再推送本地更改
"""

import os
import subprocess
import sys

def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            shell=True
        )
        return {"success": True, "stdout": result.stdout, "stderr": result.stderr}
    except subprocess.CalledProcessError as e:
        return {"success": False, "stdout": e.stdout, "stderr": e.stderr}

def sync_code(commit_message=None):
    """同步代码：先拉取，再推送"""
    print("=" * 60)
    print("代码同步工具")
    print("=" * 60)
    
    # 1. 检查当前目录
    current_dir = os.getcwd()
    print(f"当前目录: {current_dir}")
    
    # 2. 检查是否在git仓库中
    result = run_command("git rev-parse --is-inside-work-tree", current_dir)
    if not result["success"]:
        print("❌ 错误：当前目录不是git仓库")
        return False
    
    # 3. 获取当前分支
    result = run_command("git branch --show-current", current_dir)
    if not result["success"]:
        print("❌ 错误：无法获取当前分支")
        return False
    current_branch = result["stdout"].strip()
    print(f"当前分支: {current_branch}")
    
    # 4. 检查本地是否有未提交的更改
    print("\n[步骤1] 检查本地更改...")
    result = run_command("git status --porcelain", current_dir)
    if not result["success"]:
        print("❌ 错误：无法检查git状态")
        return False
    
    has_local_changes = len(result["stdout"].strip()) > 0
    if has_local_changes:
        print("⚠️ 发现本地有未提交的更改:")
        print(result["stdout"])
    else:
        print("✅ 本地工作目录干净")
    
    # 5. 拉取远程更新
    print("\n[步骤2] 从GitHub拉取最新代码...")
    result = run_command("git fetch origin", current_dir)
    if not result["success"]:
        print(f"❌ 拉取失败: {result['stderr']}")
        return False
    print("✅ 成功拉取远程更新")
    
    # 6. 检查是否有冲突
    print("\n[步骤3] 检查合并冲突...")
    result = run_command(f"git merge --no-commit --no-ff origin/{current_branch}", current_dir)
    
    if result["success"]:
        # 没有冲突，取消合并（稍后会真正合并）
        run_command("git merge --abort", current_dir)
        print("✅ 没有冲突，可以安全合并")
    else:
        # 有冲突，需要用户处理
        print("❌ 发现合并冲突！")
        print("冲突详情:")
        print(result["stderr"])
        
        # 尝试中止合并
        run_command("git merge --abort", current_dir)
        
        print("\n" + "=" * 60)
        print("⚠️ 请手动处理冲突：")
        print("1. 运行 git pull origin " + current_branch)
        print("2. 解决冲突文件")
        print("3. 运行 git add .")
        print("4. 运行 git commit")
        print("5. 运行 git push origin " + current_branch)
        print("=" * 60)
        return False
    
    # 7. 执行真正的合并
    print("\n[步骤4] 执行合并...")
    result = run_command(f"git merge --ff-only origin/{current_branch}", current_dir)
    if not result["success"]:
        print(f"❌ 合并失败: {result['stderr']}")
        return False
    print("✅ 合并成功")
    
    # 8. 如果有本地更改，提交并推送
    if has_local_changes and commit_message:
        print("\n[步骤5] 提交本地更改...")
        result = run_command(f'git add . && git commit -m "{commit_message}"', current_dir)
        if not result["success"]:
            print(f"❌ 提交失败: {result['stderr']}")
            return False
        print("✅ 提交成功")
        
        print("\n[步骤6] 推送到GitHub...")
        result = run_command(f"git push origin {current_branch}", current_dir)
        if not result["success"]:
            print(f"❌ 推送失败: {result['stderr']}")
            return False
        print("✅ 推送成功")
    elif has_local_changes:
        print("\n⚠️ 有本地更改但未提供提交消息，跳过提交")
        print("请手动执行: git add . && git commit -m 'message' && git push")
    else:
        print("\n✅ 本地无更改，无需推送")
    
    print("\n" + "=" * 60)
    print("🎉 代码同步完成！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    # 获取提交消息参数
    commit_message = None
    if len(sys.argv) > 1:
        commit_message = " ".join(sys.argv[1:])
    
    success = sync_code(commit_message)
    sys.exit(0 if success else 1)
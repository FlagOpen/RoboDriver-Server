#!/bin/bash

# 定义变量
CONTAINER_NAME="baai_flask_server"  # 替换为你的容器名
CURRENT_USER=$(whoami)
REPO_DIR="/opt/RoboDriver-Server"
BRANCH="main"  # 默认分支名（可修改为你的分支）

# 错误处理函数
handle_error() {
    echo "❌ 错误: $1" >&2
    exit 1
}

# 1. 检查并停止 Docker 容器
echo "🔍 检查容器 '${CONTAINER_NAME}' 是否运行..."
if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🛑 发现正在运行的容器 '${CONTAINER_NAME}'，正在停止..."
    sudo docker stop "${CONTAINER_NAME}" || handle_error "停止容器失败"
else
    echo "ℹ️ 容器 '${CONTAINER_NAME}' 未运行，跳过停止步骤。"
fi

# 2. 更新代码（排除 .sh, .yaml, .txt 文件）
echo "📦 正在更新 ${REPO_DIR} 的代码..."
cd "${REPO_DIR}" || handle_error "无法进入目录 ${REPO_DIR}"

# 标记文件（只需一次）.sh, .yaml, .txt 文件（避免覆盖本地修改）
git update-index --skip-worktree *.sh *.yaml *.json
# 拉取最新代码（排除特定文件类型）
echo "🔄 执行 git pull..."
git pull || handle_error "git pull 失败"

# 3. 重启 Docker 容器
if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "🚀 正在重启容器 '${CONTAINER_NAME}'..."
    sudo docker start "${CONTAINER_NAME}" || handle_error "重启容器失败"

    echo "✅ 更新完成！容器已重启。"
else
    echo "ℹ️ 容器 '${CONTAINER_NAME}' 未运行，跳过停止步骤。"
fi
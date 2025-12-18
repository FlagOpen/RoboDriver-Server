#!/bin/bash

# 错误处理函数
die() {
    echo "ERROR: $*" >&2
    exit 1
}

# ====================== 核心优化1: 自动检测架构（x86/arm） ======================
detect_architecture() {
    local arch=$(uname -m)
    case "$arch" in
        x86_64|amd64)
            echo "x86"
            ;;
        aarch64|arm64)
            echo "arm"
            ;;
        *)
            die "不支持的架构: $arch，仅支持 x86_64/amd64 或 aarch64/arm64"
            ;;
    esac
}
ARCH=$(detect_architecture)
echo "🎉 自动检测到系统架构: $ARCH"

# ====================== 核心优化2: 机器人名称记忆（基于文件存储） ======================
ROBOT_TYPE_FILE="$HOME/.robodriver_robot_type"  # 记忆文件存储路径
KNOWN_ROBOT_TYPES=("aloha" "pika" "realman" "dexterous_hand" "so101" "galaxea" "galbot")

# 读取历史机器人名称（如果存在）
if [ -f "$ROBOT_TYPE_FILE" ]; then
    LAST_ROBOT_TYPE=$(cat "$ROBOT_TYPE_FILE")
    echo -e "\n检测到上次使用的机器人名称: $LAST_ROBOT_TYPE"
    read -p "是否继续使用该名称？(y/n，默认y): " confirm
    if [[ -z "$confirm" || "$confirm" == "y" || "$confirm" == "Y" ]]; then
        robot_type="$LAST_ROBOT_TYPE"
        echo "已确认使用机器人名称: $robot_type"
    else
        # 重新输入机器人名称
        while true; do
            read -p "请输入新的机器人名称（例如：aloha, pika, realman 等）: " robot_type
            if [[ -z "$robot_type" ]]; then
                echo "错误：机器人名称不能为空，请重新输入！"
                continue
            fi
            # 检查是否是已知名称
            is_known_type=false
            for type in "${KNOWN_ROBOT_TYPES[@]}"; do
                if [[ "$robot_type" == "$type" ]]; then
                    is_known_type=true
                    break
                fi
            done
            # 未知名称二次确认
            if [[ $is_known_type == false ]]; then
                echo "警告：'${robot_type}' 不是预定义的机器人名称"
                read -p "是否确认使用此名称？(y/n): " confirm_new
                if [[ "$confirm_new" != "y" && "$confirm_new" != "Y" ]]; then
                    continue
                fi
            fi
            # 保存新名称到记忆文件
            echo "$robot_type" > "$ROBOT_TYPE_FILE"
            echo "已保存机器人名称: $robot_type"
            break
        done
    fi
else
    # 首次运行，输入机器人名称
    while true; do
        read -p "请输入您的机器人名称（例如：aloha, pika, realman 等）: " robot_type
        if [[ -z "$robot_type" ]]; then
            echo "错误：机器人名称不能为空，请重新输入！"
            continue
        fi
        # 检查是否是已知名称
        is_known_type=false
        for type in "${KNOWN_ROBOT_TYPES[@]}"; do
            if [[ "$robot_type" == "$type" ]]; then
                is_known_type=true
                break
            fi
        done
        # 未知名称二次确认
        if [[ $is_known_type == false ]]; then
            echo "警告：'${robot_type}' 不是预定义的机器人名称"
            read -p "是否确认使用此名称？(y/n): " confirm_new
            if [[ "$confirm_new" != "y" && "$confirm_new" != "Y" ]]; then
                continue
            fi
        fi
        # 保存名称到记忆文件
        echo "$robot_type" > "$ROBOT_TYPE_FILE"
        echo "已保存机器人名称: $robot_type"
        break
    done
fi

# ====================== 初始配置 ======================
echo -e "\n请注意！！！该安装程序为用户使用，适配 $ARCH 架构，安装采集平台所需的软件、服务"
read -p "按回车键继续..."

# 获取脚本所在目录（处理符号链接情况）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR" || die "无法进入脚本目录"

# 核心优化3: 按架构定义变量（无需用户干预）
if [[ "$ARCH" == "x86" ]]; then
    DOCKER_HUB_IMAGE="liuyou1103/wanx-server:tag"  # x86对应的Hub镜像
    BACKEND_ARCH_DIR="x86"
elif [[ "$ARCH" == "arm" ]]; then
    DOCKER_HUB_IMAGE="liuyou1103/wanx-server-arm:latest"  # arm对应的Hub镜像
    BACKEND_ARCH_DIR="arm"
fi

NGINX_CONFS=("baai_server_release.conf")
INSTALL_DOCKER="y"  # 默认安装Docker
BACKEND_DIR="/opt/RoboDriver-Server"
# 用户版固定配置（无需用户选择）
device_server_type="demo"
upload_type="ks3"

# 检查必需文件是否存在
REQUIRED_FILES=("${NGINX_CONFS[@]}")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        die "错误：必需文件 $file 不存在，请确保它在脚本同级目录下"
    fi
done

# 检查是否为root用户
if [ "$(id -u)" -eq 0 ]; then
    die "请使用普通用户运行此脚本，避免权限问题"
fi

# ====================== 核心优化4: 无需确认，直接使用当前用户名 ======================
CURRENT_USER=$(whoami)
echo -e "\n======================"
echo "步骤1: 获取当前用户名 - $CURRENT_USER"

# ====================== 步骤2: 网络配置 ======================
echo -e "\n======================"
echo "步骤2: 请配置网络（如使用 nmcli 或编辑 /etc/netplan/），确保优先使用 国际 网络"
read -p "按回车键继续..."

# ====================== 步骤3: 选择是否安装 Docker ======================
echo -e "\n======================"
while true; do
    read -p "是否需要安装 Docker？（后续镜像拉取、服务容器运行依赖Docker，输入 y/n）: " INSTALL_DOCKER
    case "$INSTALL_DOCKER" in
        y|Y|n|N)
            break
            ;;
        *)
            echo "输入无效！请输入 y（安装）或 n（不安装）"
            ;;
    esac
done

# ====================== 步骤4: 安装 Docker（根据用户选择执行） ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤4: 检查并安装 Docker..."
    # 检查是否已安装 Docker
    if command -v docker &>/dev/null; then
        echo "Docker 已安装，版本信息如下："
        docker --version
        echo "将用户 $USER 加入 docker 组..."
        sudo usermod -aG docker "$USER"
        echo "跳过安装步骤，但会继续执行配置和验证..."
    else
        # 安装依赖
        echo "安装必要依赖..."
        sudo apt-get update
        sudo apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release \
            apt-transport-https \
            software-properties-common
        # 添加 Docker 官方 GPG 密钥
        echo "添加 Docker 官方 GPG 密钥..."
        sudo mkdir -p /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        # 设置 Docker 稳定版仓库
        echo "配置 Docker 官方软件源..."
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
            $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        # 安装 Docker 引擎
        echo "安装 Docker 引擎..."
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        # 启动 Docker 并设置开机自启
        sudo systemctl enable docker
        sudo systemctl start docker
        # 将当前用户加入 docker 组
        echo "将用户 $USER 加入 docker 组..."
        sudo usermod -aG docker "$USER"
        echo "正在刷新组权限，部分系统需要重启终端"
        newgrp docker || true
        # 验证安装
        echo "验证 Docker 安装..."
        if ! sudo docker run --rm hello-world &>/dev/null; then
            echo "错误：Docker 安装验证失败！请检查日志。"
            exit 1
        fi
        echo "Docker 配置完成！版本信息："
        docker --version
    fi
else
    echo -e "\n======================"
    echo "步骤4: 您选择不安装 Docker，跳过 Docker 相关配置"
fi

# ====================== 步骤5: 安装 Git ======================
echo -e "\n======================"
echo "步骤5: 检查并安装 Git..."
if ! command -v git &>/dev/null; then
    sudo apt install -y git || die "Git 安装失败"
    echo "Git 安装完成"
else
    echo "Git 已安装，跳过"
fi

# ====================== 步骤6: 安装并配置 Nginx ======================
echo -e "\n======================"
echo "步骤6: 检查并安装 Nginx..."
if ! command -v nginx &>/dev/null; then
    sudo apt install -y nginx || die "Nginx 安装失败"
    echo "Nginx 安装完成"
else
    echo "Nginx 已安装，跳过"
fi
# 配置 Nginx
echo "配置 Nginx..."
for conf in "${NGINX_CONFS[@]}"; do
    sed "s|/home/agilex/|/home/$CURRENT_USER/|g" "$SCRIPT_DIR/$conf" | sudo tee "/etc/nginx/conf.d/$conf" >/dev/null
    echo "已配置 $conf 并替换用户名为 $CURRENT_USER"
done
# 修复 Nginx 启动依赖
if ! grep -q "WantedBy=multi-user.target" "/usr/lib/systemd/system/nginx.service"; then
    sudo mkdir -p /etc/systemd/system/nginx.service.d
    echo "[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/nginx.service.d/override.conf >/dev/null
    sudo systemctl daemon-reload
fi
# 启动 Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
sudo nginx -t || die "Nginx 配置测试失败，请检查 /etc/nginx/conf.d/ 下的配置文件"
sudo systemctl reload nginx || die "Nginx 重载失败"

# 配置日志目录权限
sudo mkdir -p /opt/RoboDriver-log/
sudo chown -R "$USER":"$USER" /opt/RoboDriver-log/
sudo chmod -R 777 /opt/RoboDriver-log/

# ====================== 步骤7: 安装 ffmpeg 和 portaudio19-dev ======================
echo -e "\n======================"
echo "步骤7: 检查并安装 ffmpeg 和 portaudio19-dev..."
# 安装 ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "正在安装 ffmpeg..."
    sudo apt update && sudo apt install -y ffmpeg || die "ffmpeg 安装失败"
    echo "ffmpeg 安装完成，版本信息："
    ffmpeg -version | head -n 1
else
    echo "ffmpeg 已安装，版本信息："
    ffmpeg -version | head -n 1
fi
# 安装 portaudio19-dev
if ! dpkg -l | grep -q "portaudio19-dev"; then
    echo "正在安装 portaudio19-dev..."
    sudo apt install -y portaudio19-dev || die "portaudio19-dev 安装失败"
    echo "portaudio19-dev 安装完成"
else
    echo "portaudio19-dev 已安装，跳过"
fi

# ====================== 步骤8: 部署代码（覆盖现有目录） ======================
echo -e "\n======================"
echo "步骤8: 部署代码（覆盖现有目录）..."
# 获取代码源目录（脚本所在目录的父目录）
CODE_DIR=$(dirname "$SCRIPT_DIR")
if [ -z "$CODE_DIR" ] || [ "$CODE_DIR" = "/" ] || [ "$CODE_DIR" = "." ]; then
    die "无法获取有效代码源目录！请确保脚本在项目正确目录下执行"
fi
echo "代码源目录：$CODE_DIR"
# 检查本地代码是否存在
if [ ! -d "$CODE_DIR" ]; then
    die "本地代码文件夹 $CODE_DIR 不存在！请确保该路径下有完整的后端代码"
fi
# 强制删除目标目录（如果存在），确保完全覆盖
if [ -d "$BACKEND_DIR" ]; then
    echo "目标目录 $BACKEND_DIR 已存在，正在删除..."
    sudo rm -rf "$BACKEND_DIR" || die "删除现有目录 $BACKEND_DIR 失败（权限不足）"
fi
# 重新创建目标目录并拷贝代码
sudo mkdir -p /opt || die "无法创建 /opt 目录（权限不足）"
echo "正在将本地代码从 $CODE_DIR 复制到 $BACKEND_DIR..."
sudo cp -a "$CODE_DIR/." "$BACKEND_DIR/" || die "拷贝代码失败（目标目录无写入权限或源文件损坏）"
# 设置目录权限
sudo chown -R $USER:$USER "$BACKEND_DIR" || die "设置目录所有者失败"
sudo chmod -R 777 "$BACKEND_DIR" || die "设置目录权限失败"
echo "代码拷入完成！目标目录：$BACKEND_DIR"

# ====================== 从Docker Hub拉取镜像 ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤9: 从 Docker Hub 拉取镜像..."
    img_name="baai-flask-server"
    echo "正在拉取镜像 ${DOCKER_HUB_IMAGE} ..."
    # 拉取镜像
    if ! sudo docker pull "$DOCKER_HUB_IMAGE"; then
        die "错误：拉取镜像 ${DOCKER_HUB_IMAGE} 失败，请检查网络连接或镜像名称是否正确"
    fi
    # 重命名为本地需要的镜像名
    echo "正在将镜像重命名为 ${img_name}:latest ..."
    if ! sudo docker tag "$DOCKER_HUB_IMAGE" "${img_name}:latest"; then
        die "错误：重命名镜像 ${DOCKER_HUB_IMAGE} 为 ${img_name}:latest 失败"
    fi
    echo "镜像拉取并命名完成！"
else
    echo -e "\n======================"
    echo "步骤9: 您选择不安装 Docker，跳过镜像拉取步骤"
fi

# ====================== 步骤10: 配置免密 sudo ======================
echo -e "\n======================"
echo "步骤10: 配置免密 sudo..."
echo "$CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/ip, /sbin/modprobe, /usr/sbin/ethtool" | sudo tee "/etc/sudoers.d/baai_nopasswd_$CURRENT_USER" >/dev/null

# ====================== 步骤11: 测试启动服务（仅Docker模式） ======================
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo -e "\n======================"
    echo "步骤11: 测试启动服务（运行版本：$device_server_type，上传方式：$upload_type）..."
    if [ -d "$BACKEND_DIR/$BACKEND_ARCH_DIR" ]; then
        cd "$BACKEND_DIR/$BACKEND_ARCH_DIR" || die "无法进入后端服务目录"
        echo "配置后台服务..."
        # 定义配置文件路径
        SETUP_FILE="$BACKEND_DIR/$BACKEND_ARCH_DIR/setup.yaml"
        # 检查配置文件是否存在
        if [ ! -f "$SETUP_FILE" ]; then
            die "错误: setup.yaml 配置文件不存在于 $SETUP_FILE"
        fi
        # 更新配置文件（机器人名称、运行版本、上传方式、数据集路径）
        echo "正在更新配置文件..."
        sed -i "s/^robot_type:.*/robot_type: $robot_type/" "$SETUP_FILE"
        sed -i "s/^device_server_type:.*/device_server_type: $device_server_type/" "$SETUP_FILE"
        sed -i "s/^upload_type:.*/upload_type: $upload_type/" "$SETUP_FILE"
        sed -i "s|^device_data_path: /home/[^/]*/DoRobot/dataset/|device_data_path: /home/$CURRENT_USER/DoRobot/dataset/|" "$SETUP_FILE"
        # 验证数据集路径更新成功
        if grep -q "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" "$SETUP_FILE"; then
            echo "dataset 路径已更新为：/home/$CURRENT_USER/DoRobot/dataset/"
        else
            echo "警告：未找到原有 dataset 路径格式，尝试追加配置..."
            echo "device_data_path: /home/$CURRENT_USER/DoRobot/dataset/" >> "$SETUP_FILE"
        fi
        
        # 新增：检查并停止已有 robodriver_server 容器
        echo "检查是否存在名为 robodriver_server 的容器..."
        if sudo docker ps -a --filter "name=^/robodriver_server$" --format "{{.Names}}" | grep -q "robodriver_server"; then
            echo "发现已有 robodriver_server 容器，正在停止并删除..."
            # 停止容器（忽略停止失败，避免容器已退出的情况）
            sudo docker stop robodriver_server || echo "容器 robodriver_server 已停止"
            # 删除容器（确保彻底清理）
            sudo docker rm robodriver_server || die "删除已有 robodriver_server 容器失败，请手动执行：sudo docker rm robodriver_server"
        else
            echo "未发现 robodriver_server 容器，直接启动新容器..."
        fi
        
        # 启动服务
        bash start_server_docker.sh || die "启动后端服务失败"
    else
        echo "警告: 后端服务目录 $BACKEND_DIR/$BACKEND_ARCH_DIR 不存在，跳过启动"
    fi
else
    echo -e "\n======================"
    echo "步骤11: 您选择不安装 Docker，跳过服务容器启动步骤"
fi

# ====================== 步骤12: 开机后操作 ======================
echo -e "\n======================"
echo "步骤12: 开机后操作..."
# 最终提示
if [[ "$INSTALL_DOCKER" == "y" || "$INSTALL_DOCKER" == "Y" ]]; then
    echo "请注意！！！"
    echo "1. 请自行安装机器控制程序 Robodriver 后，再开始采集"
    echo "2. 真机采集平台访问地址: http://localhost:5805/hmi"
else
    echo "请注意！！！"
    echo "1. 您未安装 Docker，服务未通过容器启动，请手动部署运行环境"
    echo "2. 请安装机器控制程序 Robodriver 后，再开始采集"
    echo "3. 真机采集平台访问地址: http://localhost:5805/hmi"
fi
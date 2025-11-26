#!/bin/bash

# ====================== 配置参数（可修改） ======================
CONTAINER_NAME="baai_flask_server"      # 容器名称
IMAGE_NAME="baai-flask-server"  # 镜像名称
#PORTS="-p 8088:8088"                    # 端口映射
ENCODE="-e PYTHONIOENCODING=utf-8"
PORTS="--network host"
PRIVILEGED="--privileged=true"          # 特权模式（谨慎使用）
RESTART_POLICY="--restart unless-stopped" # 重启策略

# 动态获取当前用户名
CURRENT_USER=$(whoami)

# 动态构建卷挂载路径
VOLUMES="-v /home/${CURRENT_USER}/DoRobot/dataset/:/home/robot/dataset/"
VOLUMES2="-v /opt/RoboDriver-Server/arm/:/app/code/"
VOLUMES3="-v /opt/RoboDriver-log/:/home/machine/"

# ====================== 逻辑部分（增强版） ======================

# 检查容器是否存在
if sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    # 容器存在，检查是否正在运行
    if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "容器 '${CONTAINER_NAME}' 正在运行。"
        # 检查是否可以进入（避免重启中）
        if ! sudo docker inspect -f '{{.State.Running}}' ${CONTAINER_NAME} | grep -q "true"; then
            echo "⚠️ 警告：容器处于非正常运行状态（可能正在重启）！"
            echo "查看日志："
            sudo docker logs --tail 20 ${CONTAINER_NAME}
            echo "尝试临时禁用重启策略并调试..."
            sudo docker update --restart=no ${CONTAINER_NAME}
            sudo docker start ${CONTAINER_NAME}  # 手动启动一次
            echo "现在可以尝试进入容器："
            echo "sudo docker exec -it ${CONTAINER_NAME} bash"
            exit 1
        fi
    else
        # 容器存在但未运行，尝试启动
        echo "启动已存在的容器 '${CONTAINER_NAME}'..."
        sudo docker start ${CONTAINER_NAME}
    fi
else
    # 容器不存在，创建并运行
    echo "创建并启动新容器 '${CONTAINER_NAME}'..."
    sudo docker run -d \
        --name ${CONTAINER_NAME} \
        -e LANG=C.UTF-8 \
        -e LC_ALL=C.UTF-8 \
        ${ENCODE} \
        ${PRIVILEGED} \
        ${RESTART_POLICY} \
        ${PORTS} \
        ${VOLUMES} \
        ${VOLUMES2} \
        ${VOLUMES3} \
        ${IMAGE_NAME}
fi

# 检查容器状态
echo -e "\n当前容器状态："
sudo docker ps -a --filter "name=${CONTAINER_NAME}" --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# 检查日志（最后10行）
echo -e "\n容器日志（最近10行）："
sudo docker logs --tail 10 ${CONTAINER_NAME}

# 提示如何进入容器
echo -e "\n进入容器命令："
echo "sudo docker exec -it ${CONTAINER_NAME} bash"

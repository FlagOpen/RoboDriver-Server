#!/bin/bash

# ====================== 配置参数（可修改） ======================
CONTAINER_NAME="baai_flask_server"      # 容器名称
IMAGE_NAME="baai-flask-server"  # 镜像名称
PORTS="--network host"                  # 使用主机网络
ENCODE="-e PYTHONIOENCODING=utf-8"      # 编码设置
PRIVILEGED="--privileged=true"          # 特权模式（谨慎使用）
RESTART_POLICY="--restart no"           # 交互式运行通常不需要重启策略

# 动态获取当前用户名
CURRENT_USER=$(whoami)

# 动态构建卷挂载路径
VOLUMES=(
    "-v /home/${CURRENT_USER}/DoRobot/dataset/:/home/robot/dataset/"
    "-v /opt/RoboDriver-Server/x86/:/app/code/"
    "-v /opt/RoboDriver-log/:/home/machine/"
)

# ====================== 逻辑部分 ======================

# 检查是否有正在运行的同名容器
if sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "发现正在运行的容器 '${CONTAINER_NAME}'，先停止并删除..."
    sudo docker stop ${CONTAINER_NAME}
    sudo docker rm ${CONTAINER_NAME}
elif sudo docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "发现已存在的容器 '${CONTAINER_NAME}'，将删除..."
    sudo docker rm ${CONTAINER_NAME}
fi

# 构建所有卷挂载参数
VOLUME_ARGS=""
for vol in "${VOLUMES[@]}"; do
    VOLUME_ARGS+=" $vol"
done

echo "正在启动交互式容器 '${CONTAINER_NAME}'..."
echo "使用的卷挂载："
for vol in "${VOLUMES[@]}"; do
    echo "  $vol"
done

# 启动交互式容器
sudo docker run -it \
    --name ${CONTAINER_NAME} \
    --gpus all \
    -e LANG=C.UTF-8 \
    -e LC_ALL=C.UTF-8 \
    -e NVIDIA_DRIVER_CAPABILITIES=all \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.535.230.02:/usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1 \
    ${ENCODE} \
    ${PRIVILEGED} \
    ${PORTS} \
    ${VOLUME_ARGS} \
    ${IMAGE_NAME} \
    bash

# 检查容器退出状态
EXIT_STATUS=$?
if [ $EXIT_STATUS -ne 0 ]; then
    echo -e "\n⚠️ 容器启动或运行失败，错误代码: $EXIT_STATUS"
    echo "查看容器日志："
    sudo docker logs ${CONTAINER_NAME}
else
    echo -e "\n容器已正常退出"
fi

# 提示是否保留容器
read -p "是否保留容器？(y/N，默认不保留) " keep_container
if [[ "$keep_container" != "y" && "$keep_container" != "Y" ]]; then
    echo "删除容器..."
    sudo docker rm ${CONTAINER_NAME}
fi

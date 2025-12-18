# 🎉 欢迎安装 RoboDriver-Server 及配套服务！
<p align="center">
  <img src="ui/robodriver_struct_1.png" alt="RoboDriver 架构图" width="70%"/>
</p>

为快速部署并使用 RoboDriver-Server，以下分别为 **外部使用者** 和 **智源研究院内部开发者** 提供专属部署指南，按需选择操作即可高效完成配置：

---

## 👤 外部使用者部署指南
具身一体化平台：https://roboxstudio.baai.ac.cn/

### 🚀 核心部署流程
#### 1. 克隆源码仓库
首先拉取 RoboDriver-Server 源码至本地：
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
```

#### 2. 进入使用者专属安装目录
```bash
cd RoboDriver-Server/setup/user/
```

#### 3. 执行一键安装脚本
根据设备架构选择对应脚本（无需手动配置基础依赖，脚本将自动完成环境初始化）：
- x86 架构：
  ```bash
  bash ./user_x86_setup.bash
  ```
- arm 架构：
  ```bash
  bash ./user_arm_setup.bash
  ```

#### 4. 跟随脚本完成关键配置
运行脚本后，按提示完成 4 项核心操作，其余步骤将自动执行：
1. 输入机器人类型（支持 aloha/pika/realman 等预定义类型，也可自定义）；
2. 确认或输入当前用户名（将自动同步到数据集存储路径 `/home/$CURRENT_USER/DoRobot/dataset/`）；
3. 选择是否安装 Docker：
   - 安装 Docker：选择从 Docker Hub 拉取镜像，并启动 RoboDriver-Server 容器；
   - 不安装 Docker：需后续手动完成运行环境部署（详见下方「环境部署」步骤）；
4. 注意：RoboDriver-Server 源码默认存放于 `/opt/` 目录，项目目录结构如下：
```
├── arm/                # arm架构相关文件
│   ├── docker/         # Docker配置目录
│   ├── environment.yml # 环境配置文件
│   ├── requirements.txt # 依赖清单
│   ├── setup.yaml      # 服务配置文件
│   ├── start_server_docker.sh # 容器启动脚本
│   └── operating_platform_server_test.py # 服务启动入口
├── logtail/            # 日志相关配置
├── setup/              # 安装脚本目录
│   ├── user/           # 用户专属脚本（当前操作目录）
│   └── developer/      # 开发者专属脚本
├── ui/                 # 前端相关资源
├── update/             # 版本更新工具
└── x86/                # x86架构相关文件（结构同arm目录）
```

#### 5. 访问采集平台
安装完成后，通过以下地址直接访问本地采集平台：
```
http://localhost:5805/hmi
```

### 🛠️ 补充操作指南
#### （一）非 Docker 环境部署（未安装 Docker 时）
若选择不安装 Docker，需手动部署运行环境，步骤如下：
1. 基于 Conda 创建并激活虚拟环境（支持 Python 3.10/3.11）：
   ```bash
   conda create -n robodriverserver python=3.11  # 以Python 3.11为例
   conda activate robodriverserver
   ```
2. 进入对应架构的服务目录：
   ```bash
   # x86架构
   cd RoboDriver-Server/x86/
   # 或 arm架构
   cd RoboDriver-Server/arm/
   ```
3. 安装依赖并启动服务：
   ```bash
   pip install -r requirements.txt  # 安装Python依赖
   python operating_platform_server_test.py  # 启动RoboDriver-Server
   ```

#### （二）容器调试操作（Docker 部署时）
若通过一键容器部署，需调试服务可按以下步骤操作：
1. 查看并停止当前容器：
   ```bash
   docker ps -a  # 查看容器状态（容器名：robodriver_server）
   docker stop robodriver_server && docker rm robodriver_server  # 停止并删除容器
   ```
2. 进入对应架构目录，启动调试容器：
   ```bash
   # x86架构
   cd RoboDriver-Server/x86/
   # 或 arm架构
   cd RoboDriver-Server/arm/
   bash debug_server_docker.sh  # 启动调试容器并进入
   ```
3. 容器内启动服务并查看日志：
   ```bash
   python operating_platform_server_test.py  # 查看服务实时输出
   ```
4. 调试完成后退出并重启正式服务：
   ```bash
   exit  # 退出调试容器（按提示选择N删除容器）
   bash start_server_docker.sh  # 重启正式服务容器
   ```
5. 日志查看路径：`/opt/RoboDriver-log/log/server/`

#### （三）上传配置与 GPU 编码说明
采集数据的上传规则与视频编码可通过 `setup.yaml` 配置，核心参数说明如下：
```yaml
# 机器人类型配置
robot_type: franka  # 已通过脚本自动设置，可手动修改
# 服务端地址配置
device_server_ip: http://localhost:8088 # 本地服务地址配置
device_server_port: 8088  # 端口号
# 上传开关与模式
is_upload: True  # 是否开启自动上传
upload_immadiately_gpu: False  # 开启GPU实时编码上传（需NVIDIA显卡）
is_collect_upload_at_sametime: False  # 采集与上传异步执行（默认False,开启GPU实时编码上传时，需改成True）
# 上传类型与时间（外部用户仅支持ks3）
upload_type: ks3  # 固定为ks3，无需修改
upload_time: '20:00'  # 定时上传时间（仅is_upload=True时生效）
```
- 当 `use_video=False` 时，采集的相机数据将以图片形式存储，触发上传后自动编码为视频存入 `video` 目录；
- 若需采集、编码、上传同步完成，需满足：
  1. 主机配备 NVIDIA 显卡；
  2. 设置 `upload_immadiately_gpu: True` && `is_collect_upload_at_sametime: True`；
  3. 通过 `start_server_docker_gpu.sh` 启动容器。

### ❌ 常见问题排查
1. 提示 `127.0.0.1:8088` 连接失败：RoboDriver-Server 服务未启动，需重新执行启动命令；
2. 访问 `http://localhost:5805/hmi` 失败：重启 Nginx 服务，命令：
   ```bash
   sudo systemctl restart nginx
   ```
3. 数据集路径权限问题：重新设置目录权限：
   ```bash
   sudo chown -R $USER:$USER /home/$CURRENT_USER/DoRobot/dataset/
   sudo chmod -R 777 /home/$CURRENT_USER/DoRobot/dataset/
   ```

---

## 👨💻 智源研究院内部开发者部署指南
具身一体化平台：https://ei2rmd.baai.ac.cn

### 🚀 核心部署流程
#### 1. 克隆源码仓库
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
```

#### 2. 进入开发者专属安装目录
```bash
cd RoboDriver-Server/setup/developer/
```

#### 3. 执行一键安装脚本
根据设备架构选择对应脚本（自动完成依赖安装、代码部署、服务配置、Logtail 日志采集配置）：
- x86 架构：
  ```bash
bash  ./developer_x86_setup.bash
  ```
- arm 架构：
  ```bash
bash  ./developer_arm_setup.bash
  ```

#### 4. 跟随脚本完成专属配置
运行脚本后，按提示完成以下配置（其余流程自动执行）：
1. 输入机器人类型（支持 aloha/pika/realman 等预定义类型，也可自定义）；
2. 确认或输入当前用户名（将自动同步到数据集存储路径 `/home/$CURRENT_USER/DoRobot/dataset/`）；
3. 选择是否安装 Docker：
   - 安装 Docker：可选择从本地加载镜像或者从 Docker Hub 拉取镜像，并启动 RoboDriver-Server 容器；
   - 不安装 Docker：需后续手动完成运行环境部署（详见下方「环境部署」步骤）；
4. 选择运行版本（默认 release）；
5. **开发者专属：选择数据上传方式**：
   - `nas`：内部私有 NAS 存储；
   - `ks3`：对象存储；
   （注：上传方式选择后将自动写入 `setup.yaml`，后续可手动修改）。

#### 5. 访问专属平台地址
- 本地采集平台：`http://localhost:5805/hmi`；

### 🛠️ 开发者补充操作指南
#### （一）上传配置精细化调整
内部开发者可通过 `setup.yaml` 灵活配置上传规则，核心参数说明如下（含专属配置）：
```yaml
# 机器人类型配置
robot_type: franka  # 脚本自动设置，可手动修改
# 服务端地址配置（内部专属）
device_server_ip: http://localhost:8088 
device_server_port: 8088  # 默认端口
# 上传开关与模式（支持GPU加速）
is_upload: True  # 是否开启自动上传
upload_immadiately_gpu: False  # 开启GPU实时编码上传（需NVIDIA显卡）
is_collect_upload_at_sametime: False  # 采集与上传异步执行（GPU编码时需设为True）
# 开发者专属：上传类型（二选一）
upload_type: nas  # 已通过脚本选择，支持手动修改为 ks3
# 上传时间配置
upload_time: '20:00'  # 定时上传时间（仅is_upload=True时生效）
# 数据集存储路径（自动同步当前用户名）
device_data_path: /home/$CURRENT_USER/DoRobot/dataset/
```

#### （二）上传方式切换说明
1. 从 NAS 切换到 KS3：
   ```bash
   # 编辑对应架构的配置文件（以x86为例）
   vi /opt/RoboDriver-Server/x86/setup.yaml
   # 修改 upload_type 为 ks3，保存退出
   upload_type: ks3
   # 重启服务（容器化部署）
   docker restart robodriver_server
   # 非容器化部署
   pkill -f operating_platform_server_test.py && python /opt/RoboDriver-Server/x86/operating_platform_server_test.py
   ```
2. 从 KS3 切换到 NAS：
   ```bash
   vi /opt/RoboDriver-Server/x86/setup.yaml
   upload_type: nas
   # 重启服务（同上）
   ```
（注：切换 NAS 上传时，需确保设备已接入内部局域网，且拥有 NAS 存储读写权限）。

#### （三）开发者专属功能
1. Logtail 日志采集（自动配置）：
   - 日志存储路径：`/opt/RoboDriver-log/log/server/`；
   - 支持日志自动上报至内部监控平台，便于问题排查和服务状态监控；

#### （四）容器化调试
```bash
# 进入对应架构目录（x86为例）
cd /opt/RoboDriver-Server/x86/
# 启动开发者调试容器（含开发依赖、调试工具）
bash debug_server_docker.sh
# 容器内启动服务（dev版本，开启调试日志）
python operating_platform_server_test.py
```

### ❌ 开发者问题排查
1. NAS 上传失败：检查设备是否接入内部局域网、NAS 权限是否过期，联系管理员重置权限；
2. 数据集路径权限问题：重新设置目录权限（脚本已自动配置，异常时手动执行）：
   ```bash
   sudo chown -R $USER:$USER /home/$CURRENT_USER/DoRobot/dataset/
   sudo chmod -R 777 /home/$CURRENT_USER/DoRobot/dataset/
   ```
3. 提示 `127.0.0.1:8088` 连接失败：RoboDriver-Server 服务未启动，需重新执行启动命令；
4. 访问 `http://localhost:5805/hmi` 失败：重启 Nginx 服务，命令：
   ```bash
   sudo systemctl restart nginx
   ```

---
# 🎉 欢迎安装 RoboDriver-Server 及配套服务！
<p align="center">
  <img src="ui/robodriver_struct_1.png" alt="RoboDriver 架构图" width="70%"/>
</p>

为快速部署并使用 RoboDriver-Server，以下为**智源研究院内部开发者** 提供专属部署指南，**外部使用者**请切换到main分支，按需选择操作即可高效完成配置：

---

## 👨💻 智源研究院内部开发者部署指南
具身一体化平台：https://ei2rmd.baai.ac.cn

### 🚀 核心部署流程
#### 1. 克隆源码仓库,执行一键安装脚本
```bash
git clone https://github.com/FlagOpen/RoboDriver-Server.git
cd ./RoboDriver-Server/
git checkout baai
cd ./setup
bash setup.bash
```

#### 2. 跟随脚本完成专属配置
运行脚本后，按提示完成以下配置（其余流程自动执行）：
1. 输入机器人类型（支持 aloha/pika/realman 等预定义类型，也可自定义）；
2. 确认或输入当前用户名（将自动同步到数据集存储路径 `/home/$CURRENT_USER/DoRobot/dataset/`）；
3. 选择是否安装 Docker：
   - 安装 Docker：可选择从本地加载镜像或者从 Docker Hub 拉取镜像，并启动 RoboDriver-Server 容器；
   - 不安装 Docker：需后续手动完成运行环境部署（详见下方「环境部署」步骤）；
4. **开发者专属：选择数据上传方式**：
   - `nas`：内部私有 NAS 存储；
   - `ks3`：对象存储；
   （注：上传方式选择后将自动写入 `setup.yaml`，后续可手动修改）。
5. 默认运行production环境，如需切换成dev\stage环境等，联系开发人员。

#### 3. 访问专属平台地址
- 本地采集平台：`http://localhost:5805/hmi/`；

### ❌ 开发者问题排查
1. NAS 上传失败：检查设备是否接入内部局域网、NAS 权限是否过期，联系管理员重置权限；
2. 数据集路径权限问题：重新设置目录权限（脚本已自动配置，异常时手动执行）：
   ```bash
   sudo chown -R $USER:$USER /home/$CURRENT_USER/DoRobot/dataset/
   sudo chmod -R 777 /home/$CURRENT_USER/DoRobot/dataset/
   ```
3. 提示 `127.0.0.1:8088` 连接失败：RoboDriver-Server 服务未启动，需重新执行启动命令；
4. 访问 `http://localhost:5805/hmi/` 失败：重启 Nginx 服务，命令：
   ```bash
   sudo systemctl restart nginx
   ```
   or
   ```
   sudo systemctl start nginx
   ```

### 🛠️ 开发者补充操作指南
#### （一）上传配置及gpu上传配置
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
1. 当RoboDriver `use_video=False` 时，采集的相机数据将以图片形式存储；触发上传操作后，系统会自动将图片编码为视频文件，并存入指定的 `video` 目录。

2. 若需实现**采集、编码、上传同步完成**（实时处理流程），需同时满足以下所有条件：
   - **硬件要求**：主机必须配备 NVIDIA 显卡（需支持 NVENC 视频编码功能，主流 Kepler 架构及以上显卡均支持）；
   - **依赖安装**：需在主机安装 NVIDIA 容器运行时依赖 `nvidia-container-runtime`；
     - 安装方式（Ubuntu 系统示例）：
       1. 配置 NVIDIA 软件源：
          ```bash
          distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
          curl -s -L https://nvidia.github.io/nvidia-container-runtime/$distribution/nvidia-container-runtime.list | sudo tee /etc/apt/sources.list.d/nvidia-container-runtime.list
          ```
       2. 更新并安装：
          ```bash
          sudo apt update && sudo apt install -y nvidia-container-runtime
          ```
       3. 重启 Docker 服务使配置生效：
          ```bash
          sudo systemctl restart docker
          ```
   - **配置要求**：在配置文件中设置 `upload_immadiately_gpu: True` **并且** `is_collect_upload_at_sametime: True`；
   - **启动方式**：通过 `start_server_docker_gpu.sh` 脚本启动容器；
   - **关键配置修正**：`start_server_docker_gpu.sh` 脚本中存在 NVIDIA 编码库的挂载配置，需根据主机实际安装的 NVIDIA 驱动版本修改文件路径中的版本号：
      - 原始配置示例：
         ```bash
         -v /usr/lib/x86_64-linux-gnu/libnvidia-encode.so.535.230.02:/usr/lib/x86_64-linux-gnu/libnvidia-encode.so.1 \
         ```
      - 修改说明：将路径中的 `535.230.02` 替换为主机实际的 NVIDIA 驱动对应版本号（需确保主机 `/usr/lib/x86_64-linux-gnu/` 目录下存在 `libnvidia-encode.so.XXX.XX` 格式的文件）；
      - 版本查询方法：在主机终端执行命令 `nvidia-smi`，输出结果中「Driver Version」字段对应的数值即为需替换的版本号（例如驱动版本为 550.54.14，则替换为 `libnvidia-encode.so.550.54.14`）。

      - **补充说明**
      - 若未安装 `nvidia-container-runtime`，容器将无法识别主机 GPU 及挂载的编码库，同步处理流程会直接失效，需优先完成该依赖安装；
      - 若未正确匹配 NVIDIA 驱动版本号，会导致容器内无法加载 `libnvidia-encode.so.1` 编码库，进而出现编码失败、程序报错或同步流程卡死；
      - 若主机无 NVIDIA 显卡、不支持 NVENC 编码，或未按上述要求安装依赖/配置/启动，将无法使用同步处理流程，仅支持「先采集图片→触发上传时编码视频」的异步模式（即 `use_video=False` 对应的基础功能）；

#### （二）上传方式切换说明
1. 从 NAS 切换到 KS3：
   ```bash
   # 编辑对应架构的配置文件（以x86为例）
   vi /opt/RoboDriver-Server/x86/setup.yaml
   # 修改 upload_type 为 ks3，保存退出
   upload_type: ks3
   ```
   #### 重启服务（容器化部署）
   ```
   docker restart robodriver_server
   ```
   #### 非容器化部署
   ```
   pkill -f operating_platform_server_test.py && python /opt/RoboDriver-Server/x86/operating_platform_server_test.py
   ```
3. 从 KS3 切换到 NAS：
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


---


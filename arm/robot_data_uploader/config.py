# ====================================================================================
# 智源机器人数据上传工具 - 配置文件
# ====================================================================================
# 
# 快速使用指南:
# 1. 切换环境: 只需修改下面的 ENVIRONMENT 变量即可
#    - "production" : 线上生产环境
#    - "test"       : 测试环境（默认）
#    - "robox"       : robox环境
#    - "stage"        : stage环境
#
# 2. 网络线路: 程序会自动检测并选择最优线路（内网专线优先，不可达时自动切换到公网）
#
# 3. 如需自定义配置: 可在 ENVIRONMENT_CONFIG 中添加新的环境配置
#
# ====================================================================================

import os
import sys
import json

# ====================
# 环境配置 - 只需修改此处即可切换环境
# ====================
ENVIRONMENT = "test"  # 可选值: "production", "test", "demo", "stage"

# 环境配置映射表
ENVIRONMENT_CONFIG = {
    "production": {
        "SERVER_URL": "http://ei2rmd.baai.ac.cn",
        "BUCKET_NAME": "baai-eai-datasets",
        "UPLOAD_TARGET": "data"
    },
    "test": {
        "SERVER_URL": "http://120.92.91.171",
        "BUCKET_NAME": "baai-eai-datasets-test",
        "UPLOAD_TARGET": "data"
    },
    "demo": {
        "SERVER_URL": "http://roboxstudio.baai.ac.cn",
        "BUCKET_NAME": "baai-eai-datasets-external",
        "UPLOAD_TARGET": "data"
    },
    "stage": {
        "SERVER_URL": "http://120.92.91.171:30083",
        "BUCKET_NAME": "baai-eai-datasets-test",
        "UPLOAD_TARGET": "data/stage"
    }
}

# 根据环境自动设置配置
_env_config = ENVIRONMENT_CONFIG.get(ENVIRONMENT, ENVIRONMENT_CONFIG["test"])
SERVER_URL = _env_config["SERVER_URL"]
BUCKET_NAME = _env_config["BUCKET_NAME"]
UPLOAD_TARGET = _env_config["UPLOAD_TARGET"]

# API 路径配置
TOKEN_PATH = "/api/eai/userAccessKey/getAccessToken"
STS_PATH = "/api/eai/userAccessKey/getKs3AccessKey"
TASK_PATH = "/api/eai/task"
START_UPLOAD_PATH = "/api/eai/dataset/upload/start"
UPDATE_UPLOAD_PATH = "/api/eai/dataset/upload/process"
COMPLETE_UPLOAD_PATH = "/api/eai/dataset/upload/complete"

# 金山云存储端点配置
ENDPOINT = "ks3-cn-beijing-internal.ksyuncs.com"  # 内网专线（优先）
ENDPOINT_BACKUP = "ks3-cn-beijing.ksyuncs.com"    # 公网线路（备用）


def load_environment_config(environment=None):
    """
    加载指定环境的配置，更新全局变量 SERVER_URL、BUCKET_NAME、UPLOAD_TARGET
    
    Args:
        environment (str, optional): 要加载的环境名称，默认使用全局 ENVIRONMENT 变量
                                    可选值："production", "test", "demo", "stage"
    
    Returns:
        dict: 加载后的环境配置字典（包含 SERVER_URL、BUCKET_NAME、UPLOAD_TARGET）
    
    Notes:
        如果指定的环境不存在，会自动 fallback 到 "test" 环境
    """
    global ENVIRONMENT, SERVER_URL, BUCKET_NAME, UPLOAD_TARGET
    
    # 如果传入了环境参数，更新全局环境变量
    if environment is not None:
        ENVIRONMENT = environment
    
    # 获取环境配置（不存在则使用test环境）
    _env_config = ENVIRONMENT_CONFIG.get(ENVIRONMENT, ENVIRONMENT_CONFIG["test"])
    
    # 更新全局配置变量
    SERVER_URL = _env_config["SERVER_URL"]
    BUCKET_NAME = _env_config["BUCKET_NAME"]
    UPLOAD_TARGET = _env_config["UPLOAD_TARGET"]
    
    # 返回加载的配置，方便外部验证
    return {
        "SERVER_URL": SERVER_URL,
        "BUCKET_NAME": BUCKET_NAME,
        "UPLOAD_TARGET": UPLOAD_TARGET
    }


def get_optimal_endpoint():
    """
    选择最优的 KS3 端点
    优先尝试内网端点，如果不可达则使用公网端点
    
    Returns:
        tuple: (endpoint, endpoint_type) 端点地址和类型描述
    """
    import socket
    from colorama import Fore
    
    # 尝试连接内网端点
    try:
        sock = socket.create_connection((ENDPOINT, 80), timeout=1)
        sock.close()
        return ENDPOINT, "内网专线"
    except (socket.timeout, socket.error, OSError):
        return ENDPOINT_BACKUP, "普通线路"

# 动态获取最优端点（启动时自动检测网络并选择）
CURRENT_ENDPOINT, ENDPOINT_TYPE = get_optimal_endpoint()
ENDPOINT = CURRENT_ENDPOINT

# 在启动时输出当前环境和端点信息
def print_config_info():
    """输出当前配置信息"""
    from colorama import Fore
    print(f"{Fore.CYAN}========== 当前配置 ==========")
    print(f"{Fore.CYAN}环境: {ENVIRONMENT}")
    print(f"{Fore.CYAN}服务器: {SERVER_URL}")
    print(f"{Fore.CYAN}存储桶: {BUCKET_NAME}")
    print(f"{Fore.CYAN}上传目标: {UPLOAD_TARGET}")
    print(f"{Fore.CYAN}端点类型: {ENDPOINT_TYPE} ({ENDPOINT})")
    print(f"{Fore.CYAN}==============================")

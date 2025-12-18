import os
import json
import time
import requests
import threading
import argparse
import sys
import math
import hashlib
from filechunkio import FileChunkIO
from concurrent.futures import ThreadPoolExecutor
from ks3.connection import Connection
from ks3.multipart import PartInfo
# TODO:打包放开
from robot_data_uploader import config
# NOTE:开发调试
# import config
from tqdm import tqdm
from io import BytesIO
from colorama import init, Fore, Style
import pyfiglet
from pyfiglet import Figlet
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# 初始化颜色输出
init(autoreset=True)

__version__ = "1.0.0"
__author__ = "DataPlatform"
# __license__ = "Apache-2.0"
__repo__ = "https://gitee.com/baai-data/baai-eai-datasuite.git"
__description__ = "机器数据上传工具,支持断点续传、进度显示和文件过滤"
__help__ = "如遇问题请及时报告反馈: dataplatform@baai.ac.cn"

# 返回码定义
class ResultCode:
    """返回码常量定义"""
    SUCCESS = 200          # 操作成功
    FAIL = 500            # 操作失败
    PARAM_ERROR = 400     # 参数错误
    NOT_FOUND = 404       # 资源未找到
    UNAUTHORIZED = 401     # 未授权
    FORBIDDEN = 403        # 禁止访问
    CONFLICT = 409         # 资源冲突
    VALIDATION_ERROR = 422 # 验证错误
    SYSTEM_ERROR = 500     # 系统错误
    UPLOAD_CANCELLED = 499 # 上传被取消

@dataclass
class UploadResult:
    """上传结果数据类"""
    code: int                    # 返回码
    msg: str                     # 返回消息
    data: Optional[Dict[str, Any]] = None  # 返回数据
    
    def is_success(self) -> bool:
        """判断是否成功"""
        return self.code == ResultCode.SUCCESS
    
    def is_failed(self) -> bool:
        """判断是否失败"""
        return self.code != ResultCode.SUCCESS
    
    @classmethod
    def success(cls, msg: str = "操作成功", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建成功结果"""
        return cls(code=ResultCode.SUCCESS, msg=msg, data=data)
    
    @classmethod
    def fail(cls, code: int = ResultCode.FAIL, msg: str = "操作失败", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建失败结果"""
        return cls(code=code, msg=msg, data=data)
    
    @classmethod
    def param_error(cls, msg: str = "参数错误", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建参数错误结果"""
        return cls(code=ResultCode.PARAM_ERROR, msg=msg, data=data)
    
    @classmethod
    def not_found(cls, msg: str = "资源未找到", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建资源未找到结果"""
        return cls(code=ResultCode.NOT_FOUND, msg=msg, data=data)
    
    @classmethod
    def conflict(cls, msg: str = "资源冲突", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建资源冲突结果"""
        return cls(code=ResultCode.CONFLICT, msg=msg, data=data)
    
    @classmethod
    def cancelled(cls, msg: str = "操作被取消", data: Optional[Dict[str, Any]] = None) -> 'UploadResult':
        """创建操作被取消结果"""
        return cls(code=ResultCode.UPLOAD_CANCELLED, msg=msg, data=data)

# 以下是原client/uploader.py的其余内容，保持不变
def print_header():
    """显示工具头信息"""
    f = Figlet(font='slant')
    print(Fore.CYAN + f.renderText('Robot Data Uploader'))
    
    print(f"{Fore.YELLOW}❖ Version{Style.RESET_ALL}: {__version__}")
    print(f"{Fore.YELLOW}❖ Author{Style.RESET_ALL}:  {__author__}")
    # print(f"{Fore.YELLOW}❖ License{Style.RESET_ALL}: {__license__}")
    print(f"{Fore.YELLOW}❖ Source{Style.RESET_ALL}:  {__repo__}")
    print("\n" + "-" * 80)

def show_banner():
    """显示程序横幅"""
    banner = pyfiglet.figlet_format("BAAI Robot Data Uploader", font="slant")
    print(f"{Fore.CYAN}{banner}")
    print(f"{Fore.CYAN}{'=' * 60}")
    print(f"{Fore.YELLOW}❖ Description{Style.RESET_ALL}: {__description__}")
    print(f"{Fore.YELLOW}❖ Version{Style.RESET_ALL}: {__version__}")
    print(f"{Fore.YELLOW}❖ Author{Style.RESET_ALL}:  {__author__}")
    print(f"{Fore.YELLOW}❖ Help{Style.RESET_ALL}:  {__help__}")

    # print(f"{Fore.YELLOW}目标存储: {config.BUCKET_NAME}")
    print(f"{Fore.CYAN}{'=' * 60}\n")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

def show_menu(current_filters, auth_method, max_workers):
    # 菜单面板
    panel = Panel(
        "[bold cyan]⋙ 智源机器人数据传输管理器 v1.0.0[/]\n[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]",
        title="[bold yellow]⎈ 主菜单[/]",
        subtitle="[dim italic]↑↓ 选择，↩ 确认[/]",
        border_style="bright_blue"
    )
    console.print(panel)

    # 选项表格
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", width=2)  # 序号列
    table.add_column(style="bold white")          # 功能列
    table.add_column(style="dim yellow")          # 状态列
    # current_filters = [ "*.txt", "*.csv", "*.json", "*.dat" , "*.tar", "*.png"]
    # auth_method = "STS"
    table.add_row("1", "📤 上传单个文件", "[请选择单个文件]")
    table.add_row("2", "📂 上传目录", "[递归上传所有匹配文件]")
    table.add_row("3", "🛡️ 设置文件过滤器", f"[当前: [bold green]{current_filters}[/]]")
    table.add_row("4", "🔑 切换认证方式", f"[当前: [bold magenta]{auth_method}[/]]")
    table.add_row("5", "⚙️ 设置上传线程数", f"[当前: [bold blue]{max_workers}[/]]")
    table.add_row("6", "⛔ 退出系统", "[bold red]安全关闭连接[/]")

    console.print(table, justify="left")
    # 动态提示
    # console.print(
    #     "[dim]┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄[/]\n"
    #     "[bold]快捷操作:[/] 支持使用命令行, [cyan]-h[/]参数帮助"
    # )
    
# 是否存在ks3中的路径分隔符“/”
def has_any_path_separator(path_str):
    return '/' in path_str[1:-1]  # 检查中间是否包含`/`
    

class BaaiRobotDataUploader:
    
    def __init__(self, use_direct_auth=False):
        # 数采平台相关参数
        self.eai_token = None
        self.eai_task_id = None
        self.eai_upload_task_id = None
        # 上传工具相关参数
        self.sts_token = None
        self.connection = None
        self.resume_dir = ".upload_resume"
        self.file_filters = ["*.*"]  # "*.txt", "*.csv", "*.json", "*.dat" , "*.tar", "*.png" # 默认文件过滤器
        self.use_direct_auth = use_direct_auth
        self.max_worker = 4
        
        # 创建断点续传目录
        if not os.path.exists(self.resume_dir):
            os.makedirs(self.resume_dir)
            
    
    def set_sts_token(self, sts_token):
        self.sts_token = sts_token
    
    def set_eai_token(self, eai_token):
        self.eai_token = eai_token
        
    def set_max_worker(self, max_worker):
        self.max_worker = max_worker
        
        
    def set_file_filters(self, filters):
        """设置文件过滤器"""
        self.file_filters = filters
    
    def _is_file_allowed(self, filename):
        """检查文件是否符合过滤规则"""
        import fnmatch
        # 如果过滤器包含"*.*"，表示允许所有文件
        if "*.*" in self.file_filters:
            return True
        # 否则检查是否匹配任一过滤规则
        return any(fnmatch.fnmatch(filename.lower(), pattern.lower()) 
                  for pattern in self.file_filters)
    
    def _get_file_md5(self, file_path):
        """计算文件MD5"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _get_file_sha256(self, file_path):
        """计算文件SHA256"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _verify_file_content(self, local_file_path, remote_key, verify_method="md5"):
        """验证本地文件和远程文件内容是否一致
        
        Args:
            local_file_path: 本地文件路径
            remote_key: 远程文件对象
            verify_method: 验证方法 ("size", "md5", "sha256", "strict")
            
        Returns:
            bool: 内容是否一致
        """
        try:
            # 获取本地文件信息
            local_size = os.path.getsize(local_file_path)
            
            # 获取远程文件信息
            remote_size = remote_key.size
            
            # 首先比较文件大小（所有验证方法都需要）
            if local_size != remote_size:
                print(f"{Fore.BLUE}文件大小不一致: 本地={local_size}, 远程={remote_size}")
                return False
            
            # 如果只是大小验证，到这里就结束了
            if verify_method == "size":
                print(f"{Fore.GREEN}文件大小验证通过: {local_size}")
                return True
            
            # 获取远程文件的ETag（通常是MD5）
            remote_etag = remote_key.etag.strip('"') if remote_key.etag else None
            
            if verify_method == "md5":
                # MD5验证
                local_md5 = self._get_file_md5(local_file_path)
                if not remote_etag:
                    print(f"{Fore.YELLOW}远程文件缺少ETag，无法进行MD5验证")
                    return False
                
                if local_md5 != remote_etag:
                    print(f"{Fore.BLUE}文件MD5不一致: 本地={local_md5}, 远程={remote_etag}")
                    return False
                
                print(f"{Fore.GREEN}文件MD5验证通过: {local_md5}")
                return True
                
            elif verify_method == "sha256":
                # SHA256验证（需要从远程文件下载计算）
                local_sha256 = self._get_file_sha256(local_file_path)
                
                # 从远程文件计算SHA256
                try:
                    remote_content = remote_key.get_contents_as_string()
                    remote_sha256 = hashlib.sha256(remote_content).hexdigest()
                    
                    if local_sha256 != remote_sha256:
                        print(f"{Fore.BLUE}文件SHA256不一致: 本地={local_sha256}, 远程={remote_sha256}")
                        return False
                    
                    print(f"{Fore.GREEN}文件SHA256验证通过: {local_sha256}")
                    return True
                except Exception as e:
                    print(f"{Fore.YELLOW}无法获取远程文件内容进行SHA256验证: {str(e)}")
                    return False
                    
            elif verify_method == "strict":
                # 严格验证：同时验证MD5和SHA256
                local_md5 = self._get_file_md5(local_file_path)
                local_sha256 = self._get_file_sha256(local_file_path)
                
                # 验证MD5
                if not remote_etag or local_md5 != remote_etag:
                    print(f"{Fore.BLUE}文件MD5验证失败: 本地={local_md5}, 远程={remote_etag}")
                    return False
                
                # 验证SHA256
                try:
                    remote_content = remote_key.get_contents_as_string()
                    remote_sha256 = hashlib.sha256(remote_content).hexdigest()
                    
                    if local_sha256 != remote_sha256:
                        print(f"{Fore.BLUE}文件SHA256验证失败: 本地={local_sha256}, 远程={remote_sha256}")
                        return False
                    
                    print(f"{Fore.GREEN}文件严格验证通过: MD5={local_md5}, SHA256={local_sha256}")
                    return True
                except Exception as e:
                    print(f"{Fore.YELLOW}无法进行严格验证: {str(e)}")
                    return False
            
            else:
                print(f"{Fore.YELLOW}不支持的验证方法: {verify_method}")
                return False
                
        except Exception as e:
            print(f"{Fore.YELLOW}文件内容验证失败: {str(e)}")
            # 验证失败时，为了安全起见，不跳过上传
            return False
    
    def _get_resume_info(self, file_path):
        """获取断点续传信息"""
        resume_file = os.path.join(
            self.resume_dir, 
            f"{self._get_file_md5(file_path)}.json"
        )
        if os.path.exists(resume_file):
            with open(resume_file, 'r') as f:
                return json.load(f)
        return None
    
    def _save_resume_info(self, file_path, info):
        """保存断点续传信息"""
        resume_file = os.path.join(
            self.resume_dir,
            f"{self._get_file_md5(file_path)}.json"
        )
        with open(resume_file, 'w') as f:
            json.dump(info, f)
    
    def _delete_resume_info(self, file_path):
        """删除断点续传信息"""
        resume_file = os.path.join(
            self.resume_dir,
            f"{self._get_file_md5(file_path)}.json"
        )
        if os.path.exists(resume_file):
            os.remove(resume_file)
    
    def get_connection(self):
        """获取连接对象，根据配置使用STS或直接认证"""
        if self.connection:
            return self.connection
        try:
            if self.use_direct_auth:
                print(f"{Fore.BLUE}使用直接认证方式...")
                self.connection = Connection(
                    access_key_id=config.ACCESS_KEY,
                    access_key_secret=config.SECRET_KEY,
                    host=config.ENDPOINT
                )
            else:
                print(f"{Fore.BLUE}使用STS临时凭证认证方式...")
                # response = requests.get(f"{config.SERVER_URL}/get_sts_token", verify=False)
                # self.sts_token = response.json()
                
                self.connection = Connection(
                    access_key_id=self.sts_token['accessKeyId'],
                    access_key_secret=self.sts_token['secretAccessKey'],
                    security_token=self.sts_token['securityToken'],
                    host=config.ENDPOINT
                )
                
            return self.connection
        except Exception as e:
            print(f"{Fore.RED}获取连接失败: {str(e)}")
            if self.use_direct_auth:
                print(f"{Fore.RED}请检查配置文件中的 ACCESS_KEY 和 SECRET_KEY 是否正确")
            else:
                print(f"{Fore.RED}STS服务可能不可用，请尝试使用直接认证方式")
            sys.exit(1)
            
    def get_ks3_sts(self):
        """获取金山云ks3的sts信息
        Args:
            token: 具身数据平台token
        Returns:
            _type_: 成功/失败
        """
        try:
            # 获取STS服务上传凭证
            headers = {"Authorization": f"Bearer {self.eai_token}"}
            response = requests.get(f"{config.SERVER_URL}{config.STS_PATH}", headers=headers)
            if "code" in response.json() and response.json()["code"]==200:
                self.sts_token = response.json()["data"]
                return True
        except Exception as e:
            print(f"{Fore.RED}获取sts凭证失败: {str(e)}")
        return False

            
                    
    def get_eai_token(self, ak, sk):
        """获取金山云ks3的sts信息
        Args:
            ak: 具身数据平台accesskey
            sk: 具身数据平台secretkey
        Returns:
            _type_: 具身数据平台token
        """
        try:
            # 获取具身真机平台token
            response = requests.post(f"{config.SERVER_URL}{config.TOKEN_PATH}", json={"ak":ak, "sk":sk})
            if response.status_code == 200:
                if "code" in response.json() and response.json()["code"]==200:
                     self.eai_token = response.json()["data"]['token']
                return self.eai_token
            return None
        except Exception as e:
            print(f"{Fore.RED}获取token失败: {str(e)}")
            
            
    def get_eai_task(self, task_id):
        """获取具身数据平台任务详情
        Args:
            task_id: 具身平台任务ID
            token: 具身数据平台token
        """
        try:
            if task_id == -99:
                self.eai_task_id = -99
                return True
            # 获取STS服务上传凭证
            headers = {"Authorization": self.eai_token}
            response = requests.get(f"{config.SERVER_URL}{config.TASK_PATH}/{task_id}", headers=headers)
            if response.status_code == 200:
                if "code" in response.json() and response.json()["code"]==200:
                    self.eai_task_id = response.json()["data"]["id"]
                    return True
            return False
        except Exception as e:
            print(f"{Fore.RED}获取具身任务失败: {str(e)}")
            
        
    def beigin_upload_eai_task(self, data):
        """开始上传数据集任务
        Args:
            data: 数据定义
        Returns:
            _type_: 成功/失败
        """
        try:
            headers = {"Authorization": self.eai_token}
            # 获取具身真机平台token
            response = requests.post(f"{config.SERVER_URL}{config.START_UPLOAD_PATH}", headers=headers, json=data)
            if response.status_code == 200:
                if "code" in response.json() and response.json()["code"]==200:
                    self.eai_upload_task_id = response.json()["data"]["uploadTaskId"]
                    return True
            print(f"{Fore.YELLOW}警告：开始上传通知异常,数据可正常上传,但后续平台无记录,请联系管理员排查。具体信息:{response.json()}")
            return False
        except Exception as e:
            print(f"{Fore.YELLOW}开始上传通知异常: {str(e)}")
            
    
    def update_upload_eai_task_progress(self, data):
        """更新数据集上传任务进度
        Args:
            data: 数据定义
        Returns:
            _type_: 成功/失败
        """
        try:
            headers = {"Authorization": self.eai_token}
            # 获取具身真机平台token
            response = requests.post(f"{config.SERVER_URL}{config.UPDATE_UPLOAD_PATH}", headers=headers, json=data)
            if response.status_code == 200:
                if "code" in response.json() and response.json()["code"]==200:
                    # self.eai_upload_task_id = response.json()["data"]["uploadTaskId"]
                    return True
            print(f"{Fore.YELLOW}警告：更新上传数据集进度通知异常,数据可正常上传,但平台进度异常,请联系管理员排查。具体信息:{response.json()}")
            return False
        except Exception as e:
            print(f"{Fore.YELLOW}警告：更新上传数据集进度通知异常: {str(e)}")
            
            
    def complete_upload_eai_task(self, status):
        """完成数据集上传
        Args:
            status: SUCCESS/FAILED
        Returns:
            _type_: 成功/失败
        """
        try:
            headers = {"Authorization": self.eai_token}
            # 获取具身真机平台token
            response = requests.post(f"{config.SERVER_URL}{config.COMPLETE_UPLOAD_PATH}", headers=headers, json={"upload_task_id":self.eai_upload_task_id, "status": status})
            if response.status_code == 200:
                if "code" in response.json() and response.json()["code"]==200:
                    # self.eai_upload_task_id = response.json()["data"]["uploadTaskId"]
                    return True
            print(f"{Fore.YELLOW}警告：完成数据集上传通知异常,数据可正常上传,但平台状态异常,请联系管理员排查。具体信息:{response.json()}")
            return False
        except Exception as e:
            print(f"{Fore.YELLOW}完成数据集上传通知异常: {str(e)}") 
            
    
    def upload_file(self, file_path, target_directory, base_dir=None, skip_exist=False, show_progress=False, verify_method="size"):
        """上传文件
        Args:
            file_path: 本地文件路径
            target_directory: 远程数据集目录
            base_dir: 基础目录路径（用于计算相对路径）
            skip_exist: 是否跳过目录存在检查
            show_progress: 是否展示进度(批量上传时默认为false)
            verify_method: 文件内容验证方法 ("size", "md5", "sha256", "strict")
            
        Returns:
            dict: 包含上传结果的字典
                - success: bool, 是否成功
                - skipped: bool, 是否跳过
                - message: str, 结果消息
                - file_path: str, 文件路径
        """
        if not target_directory:
            error_msg = "必须指定数据集名称"
            print(f"{Fore.RED}错误：{error_msg}")
            return {"success": False, "skipped": False, "message": error_msg, "file_path": file_path}
            
        if not os.path.exists(file_path):
            error_msg = f"文件不存在 - {file_path}"
            print(f"{Fore.RED}错误：{error_msg}")
            return {"success": False, "skipped": False, "message": error_msg, "file_path": file_path}
            
        if not os.path.isfile(file_path):
            error_msg = f"路径不是文件 - {file_path}"
            print(f"{Fore.RED}错误：{error_msg}")
            return {"success": False, "skipped": False, "message": error_msg, "file_path": file_path}
            
        if not self._is_file_allowed(os.path.basename(file_path)):
            skip_msg = f"跳过不符合过滤规则的文件: {file_path}"
            print(f"{Fore.YELLOW}{skip_msg}")
            return {"success": False, "skipped": True, "message": skip_msg, "file_path": file_path}
            
            
        # 最大重试次数
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                connection = self.get_connection()
                
                # 计算相对路径
                if base_dir:
                    # 将 base_dir 和 file_path 都转换为绝对路径
                    abs_base = os.path.abspath(base_dir)   # 本地数据文件所在目录的绝对路径
                    abs_file = os.path.abspath(file_path)  # 本地数据文件的绝对路径
                    
                    # 确保 file_path 在 base_dir 下
                    if not abs_file.startswith(abs_base):
                        error_msg = f"文件路径 {file_path} 不在基础目录 {base_dir} 下"
                        raise ValueError(error_msg)
                    
                    # 计算相对路径，将Windows路径分隔符转换为正斜杠
                    rel_path = os.path.relpath(abs_file, abs_base).replace('\\', '/').lstrip('/')
                    # 构建目标键,避免操作系统路径问题
                    key = f"{config.UPLOAD_TARGET}/{target_directory}/{rel_path}"
                else:
                    # 如果没有指定 base_dir，则直接使用文件名
                    key = f"{config.UPLOAD_TARGET}/{target_directory}/{os.path.basename(file_path)}"

                # 是否跳过已存在的文件
                if skip_exist:
                    # 跳过则检查是否存在当前上传文件
                    bucket = connection.get_bucket(config.BUCKET_NAME)
                    # 检查具体的文件是否存在
                    try:
                        existing = list(bucket.list(prefix=key, delimiter='/', max_keys=1))
                        if existing:
                            # 文件存在，需要验证内容是否一致
                            if self._verify_file_content(file_path, existing[0], verify_method):
                                skip_msg = f"文件已存在且内容一致，跳过上传: {file_path}"
                                print(f"{Fore.YELLOW}{skip_msg}")
                                return {"success": False, "skipped": True, "message": skip_msg, "file_path": file_path}
                            else:
                                print(f"{Fore.BLUE}文件已存在但内容不一致，将覆盖上传: {file_path}")
                    except Exception:
                        # 如果检查失败，继续上传
                        pass
                
                file_size = os.path.getsize(file_path)
                
                # 大小文件的上传逻辑
                if file_size > 5 * 1024 * 1024:  # 5MB
                    self._multipart_upload_ks3_sdk(file_path, key, show_progress)
                    # self._multipart_upload(file_path, key, show_progress)
                else:
                    self._simple_upload(file_path, key, show_progress)
                    
                success_msg = f"成功上传: {file_path} 到 {key}"
                print(f"{Fore.GREEN}{success_msg}")      
                # 上传成功，跳出循环
                return {"success": True, "skipped": False, "message": success_msg, "file_path": file_path}

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f"{Fore.YELLOW}上传失败 {file_path}: {str(e)}，正在进行第 {retry_count} 次重试...")
                else:
                    error_msg = f"上传失败 {file_path}: {str(e)}，已重试 {retry_count} 次，放弃上传"
                    print(f"{Fore.RED}{error_msg}")
                    return {"success": False, "skipped": False, "message": error_msg, "file_path": file_path}
                
                import time
                # 重试前等待一段时间
                time.sleep(2)


    
    def _handle_duplicate_dataset(self, sub_dir):
        """处理重复的数据集名称
        
        Returns:
            str or None: 返回新的数据集名称，如果用户取消则返回None
        """
        while True:
            choice = input(f"{Fore.YELLOW}目标数据集 '{sub_dir}' 已存在。请选择操作:\n"
                          f"1. 使用另一个数据集名称\n"
                          f"2. 继续使用此数据集名称\n"
                          f"3. 取消上传\n"
                          f"请选择 [1/2/3]: ")
            
            if choice == '1':
                new_name = input(f"{Fore.BLUE}请输入新的目标数据集路径: ")
                if not new_name:
                    print(f"{Fore.RED}错误：目标数据集路径不能为空")
                    continue
                if not has_any_path_separator(sub_dir):
                    print(f"{Fore.RED}错误: 必须至少含有1个路径分隔符'/',如:a/b")
                    continue
                # 递归检查新名称是否也存在
                bucket = self.get_connection().get_bucket(config.BUCKET_NAME)
                prefix = f"{config.UPLOAD_TARGET}/{new_name}"
                existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
                
                if existing:
                    return self._handle_duplicate_dataset(new_name)
                return new_name
            elif choice == '2':
                return sub_dir
            elif choice == '3':
                return None
            else:
                print(f"{Fore.RED}无效选择，请重新输入")
    
    def _simple_upload(self, file_path, key, show_progress=False):
        """简单上传"""
        file_size = os.path.getsize(file_path)
        
        if show_progress:
            pbar = tqdm(total=file_size,
                        bar_format = "{l_bar}{bar:40}| {percentage:.0f}% [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                        colour = "GREEN" , # 使用标准绿色而非十六进制颜色码
                        dynamic_ncols = True , # 自动适应终端宽度
                        unit='B', 
                        unit_scale=True, 
                        desc=os.path.basename(file_path))
        
        with open(file_path, 'rb') as f:
            bucket = self.get_connection().get_bucket(config.BUCKET_NAME)
            k = bucket.new_key(key)
            
            
            k.set_contents_from_file(f)
            if show_progress:
                pbar.update(file_size)
        
        if show_progress:
            pbar.close()
    
    def _multipart_upload(self, file_path, key, show_progress=False):
        """分片上传"""        
        chunk_size = 5 * 1024 * 1024  # 5MB分片
        file_size = os.path.getsize(file_path)
        
        bucket = self.connection.get_bucket(config.BUCKET_NAME)
        
        # 检查是否有未完成的上传
        resume_info = self._get_resume_info(file_path)
        if resume_info and resume_info['key'] == key:
            # 恢复未完成的上传
            mp = bucket.get_all_multipart_uploads(prefix=key)[0]
            upload_id = resume_info['upload_id']
            completed_parts = resume_info['completed_parts']
            
            # todo 恢复mp的part_crc_infos状态(mp对象上传时会在本地内存维护part_info，用于完成上传时校验整个文件的crc。part_info不完整会导致本地计算crc出错。)
            for part in completed_parts:
                # from ks3.multipart import PartInfo
                mp.part_crc_infos[part['PartNumber']] = PartInfo(part['PartSize'], part['Crc64ecma'])
            
            start_part = len(completed_parts) + 1
            # if show_progress:
            print(f"{Fore.GREEN}发现{key}的断点续传信息，从第 {start_part} 部分继续上传")
        else:
            # 初始化新的分片上传
            mp = bucket.initiate_multipart_upload(key)
            upload_id = mp.id
            completed_parts = []
            start_part = 1
            
        # 计算分片数量
        chunk_count = int(math.ceil(file_size * 1.0 / chunk_size))
        
        if show_progress:
            pbar = tqdm(total=file_size, 
                        bar_format = "{l_bar}{bar:40}| {percentage:.0f}% [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                        colour = "GREEN" , # 使用标准绿色而非十六进制颜色码 
                        dynamic_ncols = True , # 自动适应终端宽度
                        unit='B', 
                        unit_scale=True, 
                        desc=os.path.basename(file_path))
            completed_bytes = (start_part - 1) * chunk_size
            pbar.update(completed_bytes)
        
        try:
            for i in range(start_part - 1, chunk_count):
                offset = chunk_size * i
                bytes_to_read = min(chunk_size, file_size - offset)
                
                with FileChunkIO(file_path, 'r', offset=offset, bytes=bytes_to_read) as fp:
                    # 上传分片                   
                    part_num = i + 1
                    ret = mp.upload_part_from_file(fp, part_num=part_num)
                    
                    if show_progress:
                        pbar.update(bytes_to_read)
                    
                    completed_parts.append({
                        'PartNumber': part_num,
                        # todo 额外保存块大小、块crc64信息
                        'PartSize': bytes_to_read,
                        'ETag': ret.response_metadata.headers['ETag'],  # todo 改为了保存ETag信息
                        'Crc64ecma': ret.response_metadata.headers['x-kss-checksum-crc64ecma']
                    })
                    
                    # 保存断点续传信息
                    self._save_resume_info(file_path, {
                        'key': key,
                        'upload_id': upload_id,
                        'completed_parts': completed_parts
                    })
            
            mp.complete_upload()
            self._delete_resume_info(file_path)
         
        except Exception as e:
            print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
            raise
        finally:
            if show_progress:
                pbar.close()
    
    def _multipart_upload_ks3_sdk(self, file_path, key, show_progress=False):
        """
        使用 key.upload_file 方法进行大文件分片上传，通过回调函数展示进度
        
        Args:
            file_path: 本地文件路径
            key: 目标存储键
            show_progress: 是否显示进度条
        """
        file_size = os.path.getsize(file_path)
        
        # 准备进度条
        if show_progress:
            pbar = tqdm(total=file_size,
                        bar_format="{l_bar}{bar:40}| {percentage:.0f}% [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                        colour="GREEN",
                        dynamic_ncols=True,
                        unit='B',
                        unit_scale=True,
                        desc=os.path.basename(file_path))

            try:
                bucket = self.connection.get_bucket(config.BUCKET_NAME)
                k = bucket.new_key(key)
                
                k.upload_file(
                    filename=file_path,
                    part_size=5 * 1024 * 1024,  # 5MB 分片
                    threads_num=5,              # 5线程并发
                    resumable=True,             # 开启断点续传
                    resumable_filename=os.path.join(self.resume_dir, f"{self._get_file_md5(file_path)}.ks3resume"),
                    headers={'x-kss-storage-class': 'STANDARD'} # 标准存储
                )
                
            except Exception as e:
                print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
                raise e
            finally:
                pbar.close()
                
        else:
            # 不显示进度条的上传
            try:
                bucket = self.connection.get_bucket(config.BUCKET_NAME)
                k = bucket.new_key(key)
                
                k.upload_file(
                    filename=file_path,
                    part_size=5 * 1024 * 1024,
                    threads_num=5,
                    resumable=True,
                    resumable_filename=os.path.join(self.resume_dir, f"{self._get_file_md5(file_path)}.ks3resume"),
                    headers={'x-kss-storage-class': 'STANDARD'}
                )
            except Exception as e:
                raise e
    
    def batch_upload(self, directory=None, target_directory=None, file_list=None, skip_exist=False, show_progress=False, verify_method="size") -> UploadResult:
        """批量上传目录下的文件或指定文件列表
        
        Args:
            directory: 本地数据集目录路径（与file_list二选一）
            target_directory: 远程数据集目录路径
            file_list: 指定要上传的文件路径列表（与directory二选一）
            skip_exist: 是否跳过同名文件
            show_progress: 是否显示进度条
            verify_method: 文件内容验证方法 ("size", "md5", "sha256", "strict")
            
        Returns:
            UploadResult: 包含code、msg和data的规范化结果
                - code: 返回码 (200成功, 400参数错误, 404资源未找到, 409冲突, 500系统错误, 499取消)
                - msg: 返回消息
                - data: 返回数据，包含上传统计信息
        """
        # 参数校验
        if not target_directory:
            error_msg = "必须指定数据集路径"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
                    
        if not has_any_path_separator(target_directory):
            error_msg = "必须至少含有1个路径分隔符'/',如:a/b"
            print(f"{Fore.RED}错误: {error_msg}")
            return UploadResult.param_error(error_msg)

            
        # 检查是否同时提供了directory和file_list
        if directory is not None and file_list is not None:
            error_msg = "不能同时指定directory和file_list参数，请选择其中一种方式"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        # 检查是否至少提供了一个参数
        if directory is None and file_list is None:
            error_msg = "必须指定directory或file_list参数之一"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        # 处理文件列表模式
        if file_list is not None:
            return self._batch_upload_files(file_list, target_directory, skip_exist, show_progress, verify_method)
        
        # 处理目录模式
        return self._batch_upload_directory(directory, target_directory, skip_exist, show_progress, verify_method)
 
    def _batch_upload_files(self, file_list, target_directory, skip_exist=False, show_progress=False, verify_method="size") -> UploadResult:
        """批量上传指定文件列表
        
        Args:
            file_list: 要上传的文件路径列表
            target_directory: 远程数据集目录路径
            skip_exist: 是否跳过同名文件
            show_progress: 是否显示进度条
            verify_method: 文件内容验证方法
            
        Returns:
            UploadResult: 上传结果
        """
        # 文件列表校验
        if not isinstance(file_list, (list, tuple)):
            error_msg = "file_list参数必须是列表或元组类型"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        if not file_list:
            error_msg = "file_list不能为空"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        # 校验每个文件路径
        valid_files = []
        invalid_files = []
        total_size = 0
        
        for file_path in file_list:
            # 检查文件路径类型
            if not isinstance(file_path, str):
                invalid_files.append((file_path, "文件路径必须是字符串类型"))
                continue
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                invalid_files.append((file_path, "文件不存在"))
                continue
            
            # 检查是否为文件
            if not os.path.isfile(file_path):
                invalid_files.append((file_path, "路径不是文件"))
                continue
            
            # 检查文件是否可读
            if not os.access(file_path, os.R_OK):
                invalid_files.append((file_path, "文件不可读"))
                continue
            
            # 检查文件大小
            try:
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    invalid_files.append((file_path, "文件大小为0"))
                    continue
                total_size += file_size
            except OSError as e:
                invalid_files.append((file_path, f"获取文件大小失败: {str(e)}"))
                continue
            
            # 检查文件是否符合过滤规则
            if not self._is_file_allowed(os.path.basename(file_path)):
                invalid_files.append((file_path, "文件不符合过滤规则"))
                continue
            
            valid_files.append((file_path, file_size))
        
        # 报告无效文件
        if invalid_files:
            print(f"{Fore.YELLOW}发现 {len(invalid_files)} 个无效文件:")
            for file_path, reason in invalid_files:
                print(f"{Fore.YELLOW}  - {file_path}: {reason}")
        
        if not valid_files:
            error_msg = "没有有效的文件可以上传"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        # 检查目标目录冲突
        # connection = self.get_connection()
        # bucket = connection.get_bucket(config.BUCKET_NAME)
        # prefix = f"{config.UPLOAD_TARGET}/{target_directory}"
        # existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
        
        # if existing:
        #     new_sub_dir = self._handle_duplicate_dataset(target_directory)
        #     if not new_sub_dir:
        #         return UploadResult.cancelled("用户取消上传")
        #     target_directory = new_sub_dir
        
        print(f"{Fore.BLUE}准备上传 {len(valid_files)} 个文件 (总大小: {total_size/1024/1024:.2f}MB)...")
        
        # 执行上传
        return self._execute_upload(valid_files, target_directory, show_progress, source_type="file_list", skip_exist=skip_exist, verify_method=verify_method)
    
    def _batch_upload_directory(self, directory, target_directory, skip_exist=False, show_progress=False, verify_method="size") -> UploadResult:
        """批量上传目录下的文件
        
        Args:
            directory: 本地数据集目录路径
            target_directory: 远程数据集目录路径
            skip_exist: 是否跳过同名文件
            show_progress: 是否显示进度条
            verify_method: 文件内容验证方法
            
        Returns:
            UploadResult: 上传结果
        """
        if not os.path.exists(directory):
            error_msg = f"路径目录不存在 - {directory}"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.not_found(error_msg)
            
        if not os.path.isdir(directory):
            error_msg = f"路径不是目录 - {directory}"
            print(f"{Fore.RED}错误：{error_msg}")
            return UploadResult.param_error(error_msg)
        
        # 检查目标目录冲突
        # connection = self.get_connection()
        # bucket = connection.get_bucket(config.BUCKET_NAME)
        # prefix = f"{config.UPLOAD_TARGET}/{target_directory}"
        # existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
        
        # if existing:
        #     new_sub_dir = self._handle_duplicate_dataset(target_directory)
        #     if not new_sub_dir:
        #         return UploadResult.cancelled("用户取消上传")
        #     target_directory = new_sub_dir
            
        # 收集符合条件的文件及其大小
        files_info = []
        total_size = 0
        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if self._is_file_allowed(filename):
                    file_path = os.path.join(root, filename)
                    size = os.path.getsize(file_path)
                    files_info.append((file_path, size))
                    total_size += size
                else:
                    print(f"{Fore.YELLOW}跳过不符合过滤规则的文件: {filename}")
        
        if not files_info:
            warning_msg = f"在目录 {directory} 中没有找到符合过滤规则的文件"
            print(f"{Fore.YELLOW}警告：{warning_msg}")
            return UploadResult.param_error(warning_msg)
        
        print(f"{Fore.BLUE}找到 {len(files_info)} 个文件 (总大小: {total_size/1024/1024:.2f}MB) 准备上传...")
        
        # 执行上传
        return self._execute_upload(files_info, target_directory, show_progress, source_type="directory", base_dir=directory, skip_exist=skip_exist, verify_method=verify_method)
    
    def _execute_upload(self, files_info, target_directory, show_progress=False, source_type="directory", base_dir=None, skip_exist=False, verify_method="size") -> UploadResult:
        """执行批量上传的核心逻辑
        
        Args:
            files_info: 文件信息列表，每个元素为 (file_path, file_size)
            target_directory: 远程数据集目录路径
            show_progress: 是否显示进度条
            source_type: 来源类型 ("directory" 或 "file_list")
            base_dir: 基础目录路径（仅用于目录模式）
            skip_exist: 是否跳过已上传的文件
            verify_method: 文件内容验证方法
        Returns:
            UploadResult: 上传结果
        """
        # 按文件大小排序，便于均匀分配
        files_info.sort(key=lambda x: x[1], reverse=True)
        
        # 将文件分配给不同线程，尽量保证每个线程处理的数据量接近
        max_workers = min(self.max_worker, len(files_info)) 
        thread_files = [[] for _ in range(max_workers)]   
        thread_sizes = [0] * max_workers
        
        # 使用贪心算法分配文件
        for file_path, size in files_info:
            # 找到当前总大小最小的线程
            min_size_thread = min(range(max_workers), key=lambda i: thread_sizes[i])
            thread_files[min_size_thread].append(file_path)
            thread_sizes[min_size_thread] += size
        
        # 定义线程上传任务
        def upload_task_thread(thread_id, files, total_size):
            try:
                # 为每个线程创建独立的上传器实例
                thread_uploader = BaaiRobotDataUploader(use_direct_auth=self.use_direct_auth)
                thread_uploader.set_sts_token(self.sts_token)
                # 使用线程本地变量跟踪当前线程的成功、失败和跳过文件
                local_success_files = []
                local_failed_files = []
                local_skipped_files = []
                
                if show_progress:
                    pbar = tqdm(total=total_size, 
                            unit='B', 
                            colour = "GREEN" , # 使用标准绿色而非十六进制颜色码
                            dynamic_ncols = True , # 自动适应终端宽度
                            unit_scale=True, 
                            desc=f"🟢 线程-{thread_id}", leave=True,
                            position=thread_id)
                                    
                for file_path in files:
                    file_size = os.path.getsize(file_path)
                    try:
                        # 根据来源类型决定是否传入基础目录参数
                        if source_type == "directory" and base_dir:
                            result = thread_uploader.upload_file(
                                file_path, 
                                target_directory,
                                base_dir=base_dir,  # 添加基础目录参数
                                skip_exist=skip_exist, 
                                show_progress=False,
                                verify_method=verify_method
                            )
                        else:
                            result = thread_uploader.upload_file(
                                file_path, 
                                target_directory,
                                skip_exist=skip_exist, 
                                show_progress=False,
                                verify_method=verify_method
                            )
                        
                        # 处理上传结果
                        if result:
                            if result.get("success", False):
                                local_success_files.append(file_path)
                            elif result.get("skipped", False):
                                local_skipped_files.append(file_path)
                            else:
                                local_failed_files.append(file_path)
                        else:
                            local_failed_files.append(file_path)
                            
                    except Exception as e:
                        print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
                        local_failed_files.append(file_path)                            
                    finally:
                        if show_progress:
                            # 更新进度条
                            pbar.update(file_size)

                if show_progress:
                    pbar.close()
                return local_success_files, local_failed_files, local_skipped_files
            except Exception as e:
                print(f"{thread_id}-error:{e}")
                return [], [], []
                
        # 由于使用了tqdm的position参数来显示多个进度条
        # 需要预先打印足够的空行为进度条预留显示空间
        if show_progress:
            print("\n" * (max_workers + 1))
        
        # 使用线程池并行上传
        success_count = 0
        failure_count = 0
        skipped_count = 0
        success_files, failure_files, skipped_files = [], [], []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(max_workers):
                if thread_files[i]:  # 只为有文件的线程创建任务
                    future = executor.submit(
                        upload_task_thread,
                        i,  # thread_id
                        thread_files[i],  # 该线程负责的文件列表
                        thread_sizes[i]   # 该线程负责的文件总大小
                    )
                    futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                local_success, local_failed, local_skipped = future.result()
                success_count += len(local_success)
                success_files.extend(local_success)
                failure_count += len(local_failed)
                failure_files.extend(local_failed)
                skipped_count += len(local_skipped)
                skipped_files.extend(local_skipped)

        
        # 由于tqdm进度条会占用终端空间
        # 任务完成后需要打印相同数量的换行来"清理"这些进度条
        # 否则后续输出会紧贴在进度条上
        if show_progress:
            print("\n" * (max_workers + 1))
        
        # 计算总大小
        total_size = sum(size for _, size in files_info)
        
        # 构建返回数据
        result_data = {
            "upload_task_id": self.eai_upload_task_id,
            "total_files": len(files_info),
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_count": skipped_count,
            "success_files": success_files,
            "failure_files": failure_files,
            "skipped_files": skipped_files,
            "total_size_mb": total_size / 1024 / 1024,
            "target_directory": target_directory,
            "source_type": source_type
        }
        
        # 根据来源类型添加不同的源信息
        if source_type == "directory":
            result_data["source_directory"] = base_dir
        else:
            result_data["source_file_list"] = [file_path for file_path, _ in files_info]
        
        # 打印最终结果
        print(f"\n{Fore.GREEN}批量上传完成,上传ID:{self.eai_upload_task_id},可在数据上传传输列表查看")
        print(f"{Fore.GREEN}成功: {success_count} 个文件")
        if skipped_count > 0:
            print(f"{Fore.YELLOW}跳过: {skipped_count} 个文件")
        if failure_count > 0:
            print(f"{Fore.RED}失败: {failure_count} 个文件，文件列表:{failure_files}")
        
        # 根据失败情况返回不同的结果
        if failure_count == 0:
            if skipped_count > 0:
                success_msg = f"批量上传成功，共上传 {success_count} 个文件，跳过 {skipped_count} 个文件"
            else:
                success_msg = f"批量上传成功，共上传 {success_count} 个文件"
            return UploadResult.success(success_msg, result_data)
        elif success_count > 0:
            partial_msg = f"批量上传部分成功，成功 {success_count} 个文件，跳过 {skipped_count} 个文件，失败 {failure_count} 个文件"
            return UploadResult.fail(ResultCode.SYSTEM_ERROR, partial_msg, result_data)
        else:
            fail_msg = f"批量上传失败，所有 {failure_count} 个文件都上传失败"
            return UploadResult.fail(ResultCode.SYSTEM_ERROR, fail_msg, result_data)
 

    
# 使用示例和文档
def all_example_usage():
    """使用示例：展示如何调用优化后的batch_upload函数"""
    
    # 创建上传器实例
    uploader = BaaiRobotDataUploader(use_direct_auth=False)
    
    # 设置认证信息
    token = "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJhZG1pbiIsImxvZ2luX3VzZXJfa2V5IjoiMzlkNDRmMzEtZmUyNS00Y2ZkLTgyY2EtMGUwZDU0MDc3NzE4In0.uHKF2iyoD1ZEDc7HYjFgzpO24TrKxYGhnYtm7r8hnOGDBgE-Z3evmHgqNlQTRGy4K9cDiv59HpDFTSgbZRDY7A"
    uploader.set_eai_token(eai_token=token)
    uploader.get_ks3_sts()
    uploader.set_max_worker(4)
    # uploader.set_file_filters(["*.txt", "*.csv", "*.json"])
    
    print("=" * 60)
    print("📁 示例1: 上传目录")
    print("=" * 60)
    
    # 示例1: 上传目录
    result1 = uploader.batch_upload(
        directory="/Users/catkinliu/Desktop/nas/叠衣服_1813490901",
        target_directory="suibian/nas",
        skip_exist=False,
        show_progress=False
    )
    
    print("\n" + "=" * 60)
    print("📄 示例2: 上传文件列表")
    print("=" * 60)
    
    # 示例2: 上传文件列表
    file_list = [
        "/path/to/file1.txt",
        "/path/to/file2.csv", 
        "/path/to/file3.json"
    ]
    
    result2 = uploader.batch_upload(
        file_list=file_list,
        target_directory="suibian/files",
        skip_exist=False,
        show_progress=False
    )
    
    print("\n" + "=" * 60)
    print("📄 示例3: 文件列表校验演示")
    print("=" * 60)
    
    # 示例3: 演示文件列表校验功能
    invalid_file_list = [
        "/path/to/existing/file.txt",  # 假设这个文件存在
        "/path/to/nonexistent/file.txt",  # 不存在的文件
        "/path/to/directory",  # 目录而不是文件
        "",  # 空字符串
        123,  # 非字符串类型
        "/path/to/empty/file.txt"  # 假设这个文件大小为0
    ]
    
    result3 = uploader.batch_upload(
        file_list=invalid_file_list,
        target_directory="suibian/test",
        show_progress=False
    )
    
    print("\n" + "=" * 60)
    print("⏭️ 示例4: 跳过已存在文件")
    print("=" * 60)
    
    # 示例4: 演示跳过已存在文件的功能
    existing_files = [
        "/path/to/existing/file1.txt",  # 假设这个文件在远程已存在
        "/path/to/new/file2.txt",       # 假设这个文件在远程不存在
        "/path/to/existing/file3.csv"   # 假设这个文件在远程已存在
    ]
    
    result4 = uploader.batch_upload(
        file_list=existing_files,
        target_directory="suibian/skip_exist",
        skip_exist=True,  # 启用跳过已存在文件功能
        show_progress=False,
        verify_method="md5"  # 使用MD5验证
    )
    
    print("\n" + "=" * 60)
    print("🔍 示例5: 不同验证方法演示")
    print("=" * 60)
    
    # 示例5: 演示不同的验证方法
    test_files = [
        "/path/to/file1.txt",
        "/path/to/file2.csv"
    ]
    
    # 使用大小验证（最快但不够安全）
    result5a = uploader.batch_upload(
        file_list=test_files,
        target_directory="suibian/verify_size",
        skip_exist=True,
        show_progress=False,
        verify_method="size"
    )
    
    # 使用SHA256验证（最安全但较慢）
    result5b = uploader.batch_upload(
        file_list=test_files,
        target_directory="suibian/verify_sha256",
        skip_exist=True,
        show_progress=False,
        verify_method="sha256"
    )
    
    # 使用严格验证（同时验证MD5和SHA256）
    result5c = uploader.batch_upload(
        file_list=test_files,
        target_directory="suibian/verify_strict",
        skip_exist=True,
        show_progress=False,
        verify_method="strict"
    )

    
    # 处理返回结果
    def print_result(result, example_name):
        print(f"\n📊 {example_name} 结果:")
        if result.is_success():
            print(f"✅ 上传成功: {result.msg}")
            data = result.data
            print(f"   上传任务ID: {data['upload_task_id']}")
            print(f"   成功文件数: {data['success_count']}")
            if data.get('skipped_count', 0) > 0:
                print(f"   跳过文件数: {data['skipped_count']}")
                print(f"   跳过文件列表: {data['skipped_files']}")
            print(f"   总文件大小: {data['total_size_mb']:.2f}MB")
            print(f"   来源类型: {data['source_type']}")
            if data['source_type'] == 'directory':
                print(f"   源目录: {data['source_directory']}")
            else:
                print(f"   源文件列表: {data['source_file_list']}")
        else:
            print(f"❌ 上传失败: {result.msg}")
            if result.code == ResultCode.PARAM_ERROR:
                print("   错误类型: 参数错误")
            elif result.code == ResultCode.NOT_FOUND:
                print("   错误类型: 资源未找到")
            elif result.code == ResultCode.CONFLICT:
                print("   错误类型: 资源冲突")
            elif result.code == ResultCode.UPLOAD_CANCELLED:
                print("   错误类型: 用户取消")
            elif result.code == ResultCode.SYSTEM_ERROR:
                print("   错误类型: 系统错误")
                if result.data:
                    print(f"   失败文件数: {result.data['failure_count']}")
                    print(f"   失败文件列表: {result.data['failure_files']}")
                    if result.data.get('skipped_count', 0) > 0:
                        print(f"   跳过文件数: {result.data['skipped_count']}")
                        print(f"   跳过文件列表: {result.data['skipped_files']}")
    
    # 打印所有示例的结果
    print_result(result1, "目录上传")
    print_result(result2, "文件列表上传")
    print_result(result3, "文件列表校验")
    print_result(result4, "跳过已存在文件")
    print_result(result5a, "大小验证")
    print_result(result5b, "SHA256验证")
    print_result(result5c, "严格验证")

def example_usage():
    """使用示例：展示如何调用优化后的batch_upload函数"""
    
    # 创建上传器实例
    uploader = BaaiRobotDataUploader(use_direct_auth=False)
    # 设置认证信息
    token = "eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJsaXV4dSIsImxvZ2luX3VzZXJfa2V5IjoiNjA4YjIyMjctNWYyOS00YTdkLTliNGQtZmJjNTNkY2I0YWQxIn0.NT00DxqjCNuIPavgGXworBz6qXWO70r75Mlnrk-amBiHFV0fdqZsj2Gvrg5gWK81ArYPShwDCQe8uWjlGDyRzw"
    uploader.set_eai_token(eai_token=token)
    uploader.set_max_worker(4)
    if uploader.get_ks3_sts():
    
        print("\n" + "=" * 60)
        print("🔍 示例5: 不同验证方法演示")
        print("=" * 60)
        
        # 示例5: 演示不同的验证方法
        test_files = [
            "/Users/catkinliu/Desktop/数据/鸡蛋/episode_4.hdf5",
            # "/Users/catkinliu/Desktop/数据/episode0.zip"
        ]
        
        # 使用大小验证（最快但不够安全）
        result5a = uploader.batch_upload(
            file_list=test_files,
            target_directory="suibian/verify_size",
            skip_exist=True
        )
    
    
    

def get_result_code_meaning(code: int) -> str:
    """获取返回码的含义说明
    
    Args:
        code: 返回码
        
    Returns:
        str: 返回码的含义说明
    """
    code_meanings = {
        ResultCode.SUCCESS: "操作成功",
        ResultCode.FAIL: "操作失败",
        ResultCode.PARAM_ERROR: "参数错误 - 输入参数不符合要求",
        ResultCode.NOT_FOUND: "资源未找到 - 指定的路径或资源不存在",
        ResultCode.UNAUTHORIZED: "未授权 - 缺少有效的认证信息",
        ResultCode.FORBIDDEN: "禁止访问 - 没有权限访问指定资源",
        ResultCode.CONFLICT: "资源冲突 - 目标路径已存在，需要重命名",
        ResultCode.VALIDATION_ERROR: "验证错误 - 数据验证失败",
        ResultCode.SYSTEM_ERROR: "系统错误 - 系统内部错误或网络问题",
        ResultCode.UPLOAD_CANCELLED: "上传被取消 - 用户主动取消操作"
    }
    return code_meanings.get(code, f"未知返回码: {code}")

if __name__ == "__main__":
    # 显示返回码说明
    print("📋 返回码说明:")
    for code in [ResultCode.SUCCESS, ResultCode.PARAM_ERROR, ResultCode.NOT_FOUND, 
                 ResultCode.CONFLICT, ResultCode.SYSTEM_ERROR, ResultCode.UPLOAD_CANCELLED]:
        print(f"   {code}: {get_result_code_meaning(code)}")
    print()
    
    # 运行使用示例
    example_usage()
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
# 初始化颜色输出
init(autoreset=True)

__version__ = "1.0.0"
__author__ = "DataPlatform"
# __license__ = "Apache-2.0"
__repo__ = "https://gitee.com/baai-data/baai-eai-datasuite.git"
__description__ = "机器数据上传工具,支持断点续传、进度显示和文件过滤"
__help__ = "如遇问题请及时报告反馈: dataplatform@baai.ac.cn"

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
        f"[bold cyan]⋙ 智源机器人数据传输管理器 v1.0.0[/]\n[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/]\n[dim]当前线路: {config.ENDPOINT_TYPE} ({config.ENDPOINT})[/]",
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
    
class RobotDataUploader:
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
    
    def get_connection(self, show_progress=True):
        """获取连接对象，根据配置使用STS或直接认证"""
        if self.connection:
            return self.connection
        try:
            if self.use_direct_auth:
                if show_progress:
                    print(f"{Fore.BLUE}使用直接认证方式...")
                self.connection = Connection(
                    access_key_id=config.ACCESS_KEY,
                    access_key_secret=config.SECRET_KEY,
                    host=config.ENDPOINT,
                    enable_crc=False
                )
            else:
                if show_progress:
                    print(f"{Fore.BLUE}使用STS临时凭证认证方式...")
                # response = requests.get(f"{config.SERVER_URL}/get_sts_token", verify=False)
                # self.sts_token = response.json()
                
                self.connection = Connection(
                    access_key_id=self.sts_token['accessKeyId'],
                    access_key_secret=self.sts_token['secretAccessKey'],
                    security_token=self.sts_token['securityToken'],
                    host=config.ENDPOINT,
                    enable_crc=False
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
            return False
        except Exception as e:
            print(f"{Fore.RED}获取sts凭证失败: {str(e)}")
            
                    
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
            
    
    def upload_file(self, file_path, target_directory, base_dir=None, skip_dir_check=False, show_progress=True, pbar=None):
        """上传文件
        Args:
            file_path: 本地文件路径
            target_directory: 远程数据集目录
            base_dir: 基础目录路径（用于计算相对路径）
            skip_dir_check: 是否跳过目录存在检查
            show_progress: 是否显示详细的上传进度(单文件上传时为True,可展示进度条等)
            pbar: 外部传入的进度条对象（用于批量上传时复用）
        """
        if not target_directory:
            print(f"{Fore.RED}错误：必须指定数据集名称")
            return
            
        if not os.path.exists(file_path):
            print(f"{Fore.RED}错误：文件不存在 - {file_path}")
            return
            
        if not os.path.isfile(file_path):
            print(f"{Fore.RED}错误：路径不是文件 - {file_path}")
            return
            
        if not self._is_file_allowed(os.path.basename(file_path)):
            print(f"{Fore.YELLOW}跳过不符合过滤规则的文件: {file_path}")
            return
            
            
        total_file_count, success_file_count, failed_file_count= 1, 0, 0
        if show_progress:
            # 通知具身数据平台开始上传
            data = {
                "eai_task_id": self.eai_task_id,    # 任务id
                "task_name": target_directory,  # 上传任务对应的数据集
                "source_path": file_path,  # 源：数据集源路径
                "target_root_path": target_directory,  # 目标：ks3该数据集根路径
                "target_full_path": target_directory,      # 目标：数据集ks3全路径
                "total_file_count": total_file_count,  # 数据集的总文件数量
                "total_size_bytes": os.path.getsize(file_path)  # 数据集大小（字节）
            }
            if not self.beigin_upload_eai_task(data=data):
                print(f"{Fore.YELLOW}警告：开始上传通知异常,数据可正常上传,但后续平台无记录,请联系管理员排查。具体信息:{data}")
            
        # 最大重试次数
        max_retries = 5
        retry_count = 0
        try:
            while retry_count < max_retries:
                try:
                    connection = self.get_connection(show_progress)
                    
                    # 计算相对路径
                    if base_dir:
                        # 将 base_dir 和 file_path 都转换为绝对路径
                        abs_base = os.path.abspath(base_dir)   # 本地数据文件所在目录的绝对路径
                        abs_file = os.path.abspath(file_path)  # 本地数据文件的绝对路径
                        
                        # 确保 file_path 在 base_dir 下
                        if not abs_file.startswith(abs_base):
                            raise ValueError(f"文件路径 {file_path} 不在基础目录 {base_dir} 下")
                        
                        # 计算相对路径，将Windows路径分隔符转换为正斜杠
                        rel_path = os.path.relpath(abs_file, abs_base).replace('\\', '/').lstrip('/')
                        
                        # 构建目标键,避免操作系统路径问题
                        # key = os.path.join(config.UPLOAD_TARGET, sub_dir, rel_path)
                        key = f"{config.UPLOAD_TARGET}/{target_directory}/{rel_path}"
                    else:
                        # 如果没有指定 base_dir，则直接使用文件名
                        # key = os.path.join(config.UPLOAD_TARGET, sub_dir, os.path.basename(file_path))
                        key = f"{config.UPLOAD_TARGET}/{target_directory}/{os.path.basename(file_path)}"

                    # 只在单文件上传且未指定跳过时检查目录是否存在
                    if not skip_dir_check:
                        # 检查数据集是否已存在
                        bucket = connection.get_bucket(config.BUCKET_NAME)
                        # prefix = os.path.join(config.UPLOAD_TARGET, sub_dir)
                        prefix = f"{config.UPLOAD_TARGET}/{target_directory}"
                        existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
                        
                        if existing:
                            new_sub_dir = self._handle_duplicate_dataset(target_directory)
                            if not new_sub_dir:
                                return  # 用户取消上传
                            target_directory = new_sub_dir
                        # key = os.path.join(config.UPLOAD_TARGET, sub_dir, os.path.basename(file_path))
                        key = f"{config.UPLOAD_TARGET}/{target_directory}/{os.path.basename(file_path)}"
                    file_size = os.path.getsize(file_path)
                    
                    # 大小文件的上传逻辑
                    if file_size > 5 * 1024 * 1024:  # 5MB
                        # self._multipart_upload(file_path, key, show_progress)
                        self._multipart_upload_ks3_sdk(file_path, key, show_progress, pbar=pbar)
                        # self._upload_large_file_with_progress(file_path, key, show_progress)
                    else:
                        self._simple_upload(file_path, key, show_progress, pbar=pbar)
                        
                    if show_progress and not pbar:
                        print(f"{Fore.GREEN}成功上传: {file_path} 到 {key}")      
                    # 上传成功，跳出循环
                    success_file_count += 1
                    break
    
                except Exception as e:
                    retry_count += 1
                    # if show_progress:
                    if retry_count < max_retries:
                        print(f"{Fore.YELLOW}上传失败 {file_path}: {str(e)}，正在进行第 {retry_count} 次重试...")
                    else:
                        print(f"{Fore.RED}上传失败 {file_path}: {str(e)}，已重试 {retry_count} 次，放弃上传")
                    
                    if retry_count >= max_retries:
                        failed_file_count += 1
                        raise  # 重试次数用完，抛出异常
                        # break
                    import time
                    # 重试前等待一段时间
                    time.sleep(2)
                
        finally:
            if show_progress:
                # 更新进度数据
                progress_data = {
                    "upload_task_id": self.eai_upload_task_id,   # 上传数据任务id
                    "success_file_count": success_file_count,   # 已成功上传文件数量
                    "failed_file_count": failed_file_count       # 上传失败文件数量
                }
                # 调用进度更新接口
                self.update_upload_eai_task_progress(progress_data)
                # 3.通知具身数据平台完成上传
                self.complete_upload_eai_task(status="SUCCESS")


    
    def _handle_duplicate_dataset(self, sub_dir, show_progress=True):
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
                bucket = self.get_connection(show_progress).get_bucket(config.BUCKET_NAME)
                prefix = f"{config.UPLOAD_TARGET}/{new_name}"
                existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
                
                if existing:
                    return self._handle_duplicate_dataset(new_name, show_progress)
                return new_name
            elif choice == '2':
                return sub_dir
            elif choice == '3':
                return None
            else:
                print(f"{Fore.RED}无效选择，请重新输入")
    
    def _simple_upload(self, file_path, key, show_progress=True, pbar=None):
        """简单上传"""
        file_size = os.path.getsize(file_path)
        
        # 如果没有传入外部进度条且需要显示进度，则创建新的进度条
        local_pbar = None
        current_pbar = pbar
        
        if show_progress and pbar is None:
            local_pbar = tqdm(total=file_size,
                        bar_format = "{l_bar}{bar:40}| {percentage:.0f}% [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                        colour = "GREEN" , # 使用标准绿色而非十六进制颜色码
                        dynamic_ncols = True , # 自动适应终端宽度
                        unit='B', 
                        unit_scale=True, 
                        desc=os.path.basename(file_path))
            current_pbar = local_pbar
        
        # 简单上传无法获取实时进度回调，只能在开始或结束时更新
        # 或者模拟进度（不推荐）
        # 考虑到 KS3 SDK 的 set_contents_from_file 是阻塞的且没有回调参数
        # 我们只能在上传完成后一次性更新进度
        
        with open(file_path, 'rb') as f:
            bucket = self.get_connection(show_progress).get_bucket(config.BUCKET_NAME)
            k = bucket.new_key(key)
            
            k.set_contents_from_file(f)
            
            # 上传完成后更新进度
            if current_pbar:
                current_pbar.update(file_size)
        
        if local_pbar:
            local_pbar.close()
    
    def _multipart_upload(self, file_path, key, show_progress=True):
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
            if show_progress:
                print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
            raise
        finally:
            if show_progress:
                pbar.close()
    
    def _multipart_upload_ks3_sdk(self, file_path, key, show_progress=True, pbar=None):
        """
        使用金山云SDK原生方式实现的分片上传，支持断点续传
        替代原有的 _multipart_upload 方法
        参考文档: https://docs.ksyun.com/documents/40532?type=3
        """
        # 分片大小 5MB
        chunk_size = 5 * 1024 * 1024
        file_size = os.path.getsize(file_path)
        # 计算分片数量
        chunk_count = int(math.ceil(file_size * 1.0 / chunk_size))
        
        bucket = self.connection.get_bucket(config.BUCKET_NAME)
        
        mp = None
        uploaded_parts_map = {} # part_number -> Part
        
        # 1. 检查是否存在未完成的分片上传任务（断点续传）
        # 获取该key下的所有分片上传任务
        # 注意：get_all_multipart_uploads 返回的是Bucket下的所有分片任务，需要过滤
        all_uploads = bucket.get_all_multipart_uploads(prefix=key)
        for upload in all_uploads:
            if upload.key_name == key:
                mp = upload
                break
        
        if mp:
            # if show_progress and pbar is None:
            print(f"{Fore.GREEN}发现未完成的上传任务 (ID: {mp.id})，正在获取已上传分片信息...")
            
            # 获取已上传的分片
            # 使用SDK提供的迭代器自动处理分页，获取所有已上传分片
            for part in mp:
                uploaded_parts_map[part.part_number] = part
                # 尝试从 part 对象中恢复 CRC64 信息
                # 注意：这依赖于 KS3 SDK 在 ListParts 时是否返回并解析了 Crc64ecma
                # 如果 part 对象有该属性（通常是扩展属性或通过 xml 解析得到），则赋值
                # 如果没有，后续 complete_upload 仍可能报错，需要 catch 处理
                # if hasattr(part, 'crc64ecma') and part.crc64ecma:
                #      mp.part_crc_infos[part.part_number] = PartInfo(part.size, part.crc64ecma)
                # elif hasattr(part, 'last_modified'): # 只要是有效的part
                #      # 如果没有 CRC 信息，我们在服务端模式下也无法凭空捏造。
                #      # 但为了兼容 _multipart_upload 的逻辑，我们可以在这里尝试查找本地是否碰巧有记录
                #      # (虽然 _multipart_upload_ks3_sdk 旨在摆脱本地记录依赖)
                     
                #      # 尝试从本地断点续传文件补充 CRC 信息 (混合模式)
                #      resume_info = self._get_resume_info(file_path)
                #      if resume_info and resume_info.get('upload_id') == mp.id:
                #          for p in resume_info.get('completed_parts', []):
                #              if p['PartNumber'] == part.part_number:
                #                  mp.part_crc_infos[part.part_number] = PartInfo(p['PartSize'], p['Crc64ecma'])
                #                  break

            # if show_progress and pbar is None:
            print(f"{Fore.GREEN}已完成分片: {len(uploaded_parts_map)}/{chunk_count}")
        else:
            # 初始化新的分片上传任务
            # x-kss-storage-class: STANDARD (标准) / STANDARD_IA (低频)
            headers = {"x-kss-storage-class": "STANDARD"}
            mp = bucket.initiate_multipart_upload(key, headers=headers)
            if show_progress and pbar is None:
                print(f"{Fore.GREEN}初始化新的上传任务 (ID: {mp.id})")

        # 2. 准备进度条
        local_pbar = None
        current_pbar = pbar
        # 计算已上传的字节数
        completed_bytes = 0
        for part in uploaded_parts_map.values():
            completed_bytes += part.size
            
        if show_progress and pbar is None:
            local_pbar = tqdm(total=file_size,
                        initial=completed_bytes,
                        bar_format="{l_bar}{bar:40}| {percentage:.0f}% [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
                        colour="GREEN",
                        dynamic_ncols=True,
                        unit='B',
                        unit_scale=True,
                        desc=os.path.basename(file_path))
            current_pbar = local_pbar
        # 更新进度条
        current_pbar.update(completed_bytes)
        try:
            # 3. 上传未完成的分片
            # 记录本次上传的分片信息，以便更新本地缓存（可选，用于辅助下一次 CRC 恢复）
            current_session_parts = []
            
            for i in range(chunk_count):
                part_number = i + 1
                
                # 如果该分片已上传，则跳过
                if part_number in uploaded_parts_map:
                    continue
                
                offset = i * chunk_size
                bytes_to_read = min(chunk_size, file_size - offset)
                
                # 使用FileChunkIO读取指定分片的数据
                with FileChunkIO(file_path, 'r', offset=offset, bytes=bytes_to_read) as fp:
                    # 上传分片
                    ret = mp.upload_part_from_file(fp, part_num=part_number)
                    
                    # 收集本次上传的分片信息，用于更新本地缓存
                    # if ret and hasattr(ret, 'response_metadata'):
                    #     crc64 = ret.response_metadata.headers.get('x-kss-checksum-crc64ecma')
                    #     etag =ret.response_metadata.headers.get('ETag')
                    #     if crc64:
                    #          part_info = {
                    #             'PartNumber': part_number,
                    #             'PartSize': bytes_to_read,
                    #             'Crc64ecma': crc64,
                    #             'ETag': etag
                    #         }
                    #          current_session_parts.append(part_info)
                    #          # 同时更新 mp 对象的内存状态，增加成功的几率
                    #          mp.part_crc_infos[part_number] = PartInfo(bytes_to_read, crc64)
                             
                    #          # 实时更新本地断点续传信息，每上传一个分片就保存一次
                    #          # 虽然增加了IO开销，但保证了断点续传的实时性
                    #          resume_info = self._get_resume_info(file_path) or {
                    #              'key': key,
                    #              'upload_id': mp.id,
                    #              'completed_parts': []
                    #          }
                             
                    #          # 确保 upload_id 匹配，如果不匹配说明是新的任务，重置 completed_parts
                    #          if resume_info.get('upload_id') != mp.id:
                    #              resume_info = {'key': key, 'upload_id': mp.id, 'completed_parts': []}
                             
                    #          # 将新上传的分片添加到记录中
                    #          # 简单起见，直接追加，保存时去重在 _save_resume_info 中通常不做，
                    #          # 但我们为了保持文件整洁，可以读取-更新-保存
                             
                    #          # 效率优化：不需要每次都重新读取整个列表再去重
                    #          # 只需要将当前 part_info 追加到 completed_parts 并保存
                    #          resume_info['completed_parts'].append(part_info)
                    #          self._save_resume_info(file_path, resume_info)

                
                if current_pbar:
                    current_pbar.update(bytes_to_read)

            
            # 4. 完成分片上传
            # SDK会自动合并分片
            try:
                mp.complete_upload()
                # 成功后清理本地缓存
                # self._delete_resume_info(file_path)
            except Exception as e:
                # 处理断点续传时的CRC不一致问题
                # 由于无法获取旧分片的CRC信息，会导致本地计算CRC与服务端不一致
                # 但此时服务端实际上已经合并成功（否则不会返回server_crc）
                if "Inconsistent CRC checksum" in str(e):
                    if show_progress and pbar is None:
                        print(f"{Fore.YELLOW}警告: CRC校验不一致(断点续传导致)，但上传已完成。")
                    # 成功后清理本地缓存
                    # self._delete_resume_info(file_path)
                else:
                    raise e
            
            if local_pbar:
                local_pbar.close()
                # print(f"{Fore.GREEN}上传成功: {key}")
                
        except Exception as e:
            if local_pbar:
                local_pbar.close()
            if show_progress and pbar is None:
                print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
            # 抛出异常以便上层重试逻辑捕获
            raise e

    def _upload_large_file_with_progress(self, file_path, key, show_progress=True):
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

    
    def batch_upload(self, directory, target_directory):
        """批量上传目录下的文件
        
        Args:
            directory: 本地数据集目录路径
            target_directory: 远程数据集目录路径
        """
        if not target_directory:
            print(f"{Fore.RED}错误：必须指定数据集路径")
            return
            
        if not os.path.exists(directory):
            print(f"{Fore.RED}错误：路径目录不存在 - {directory}")
            return
            
        if not os.path.isdir(directory):
            print(f"{Fore.RED}错误：路径不是目录 - {directory}")
            return
            
        connection = self.get_connection()
        
        # 在批量上传开始前检查一次目录是否存在
        bucket = connection.get_bucket(config.BUCKET_NAME)
        # prefix = os.path.join(config.UPLOAD_TARGET, sub_dir)
        prefix = f"{config.UPLOAD_TARGET}/{target_directory}"

        existing = list(bucket.list(prefix=prefix, delimiter='/', max_keys=1))
        
        if existing:
            new_sub_dir = self._handle_duplicate_dataset(target_directory)
            if not new_sub_dir:
                return  # 用户取消上传
            target_directory = new_sub_dir
            
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
            print(f"{Fore.YELLOW}警告：在目录 {directory} 中没有找到符合过滤规则的文件")
            return
            
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
        
        print(f"{Fore.BLUE}找到 {len(files_info)} 个文件 (总大小: {total_size/1024/1024:.2f}MB) 准备上传...")
        # 1.通知具身数据平台开始上传
        data = {
            "eai_task_id": self.eai_task_id,    # 任务id
            "task_name": target_directory,  # 上传任务对应的数据集
            "source_path": directory,  # 源：数据集源路径
            "target_root_path": target_directory,  # 目标：ks3该数据集根路径
            "target_full_path": target_directory,      # 目标：数据集ks3全路径
            "total_file_count": len(files_info),  # 数据集的总文件数量
            "total_size_bytes": total_size  # 数据集大小（字节）
        }
        self.beigin_upload_eai_task(data=data)
        
        # 定义线程上传任务
        def upload_task_thread(thread_id, files, total_size, shared_success_files, shared_failed_files, lock):
            # 为每个线程创建独立的上传器实例
            thread_uploader = RobotDataUploader(use_direct_auth=self.use_direct_auth)
            thread_uploader.set_sts_token(self.sts_token)
            # 使用线程本地变量跟踪当前线程的成功和失败文件
            local_success_files = []
            local_failed_files = []
            
            # 添加进度更新计时器
            last_update_time = time.time()
            
            with tqdm(total=total_size, 
                     unit='B', 
                     colour = "GREEN" , # 使用标准绿色而非十六进制颜色码
                     dynamic_ncols = True , # 自动适应终端宽度
                     unit_scale=True, 
                     desc=f"🟢 线程-{thread_id}", leave=True,
                     position=thread_id) as pbar:                
                for file_path in files:
                    try:
                        # 传入基础目录路径
                        thread_uploader.upload_file(
                            file_path, 
                            target_directory,
                            base_dir=directory,  # 添加基础目录参数
                            skip_dir_check=True, 
                            show_progress=False, # 批量上传时，内部不再打印单个文件的进度条信息，但会通过pbar更新进度
                            pbar=pbar # 传入当前线程的进度条对象
                        )
                        local_success_files.append(file_path)
                        # 更新共享成功列表
                        with lock:
                            shared_success_files.append(file_path)
                        
                        # 更新进度条
                        # 注意：upload_file内部已经调用了pbar.update来更新实际上传的字节数
                        # 这里不需要再次 update file_size，否则会导致进度条翻倍或溢出
                        # pbar.update(file_size) 
                    except Exception as e:
                        print(f"{Fore.RED}上传失败 {file_path}: {str(e)}")
                        local_failed_files.append(file_path)
                        # 更新共享失败列表
                        with lock:
                            shared_failed_files.append(file_path)
                            
                        # 失败的情况下，upload_file内部可能没有完全update进度
                        # 为了保证进度条能走到终点（或者至少反映该文件已处理完毕），
                        # 可以选择在这里补齐剩余的进度，或者仅仅记录失败。
                        # 通常做法是，如果任务失败了，进度条可能不会满，这能反映出问题。
                        # 但为了让总进度条看起来"完成"了当前任务的处理，可以手动补齐该文件的大小。
                        # 不过需要计算已上传的部分，比较复杂。
                        # 简单起见，如果是失败，我们假设该文件的进度没有完成。
                        # 或者，我们可以选择强制更新该文件的进度，以避免进度条卡住。
                        # file_size = os.path.getsize(file_path)
                        # pbar.update(file_size)
                
                return local_success_files, local_failed_files
        
        # 定义进度更新线程函数
        def update_progress_thread(shared_success_files, shared_failed_files, lock, stop_event):
            # 使用当前实例而不是创建新的实例
            while not stop_event.is_set():
                # 获取当前共享列表的长度
                with lock:
                    success_count = len(shared_success_files)
                    failed_count = len(shared_failed_files)
                
                # 更新进度数据
                progress_data = {
                    "upload_task_id": self.eai_upload_task_id,   # 上传数据任务id
                    "success_file_count": success_count,   # 已成功上传文件数量
                    "failed_file_count": failed_count       # 上传失败文件数量
                }
                
                # 调用进度更新接口
                self.update_upload_eai_task_progress(progress_data)
                # print("haha")
                
                # 每5秒更新一次
                time.sleep(5)
            
            # 上传完成后，发送最终进度更新
            with lock:
                success_count = len(shared_success_files)
                failed_count = len(shared_failed_files)
            
            final_progress_data = {
                "upload_task_id": self.eai_upload_task_id,   # 上传数据任务id
                "success_file_count": success_count,   # 已成功上传文件数量
                "failed_file_count": failed_count       # 上传失败文件数量
            }
            self.update_upload_eai_task_progress(final_progress_data)
            # print("hehe")

        
        # 由于使用了tqdm的position参数来显示多个进度条
        # 需要预先打印足够的空行为进度条预留显示空间
        print("\n" * (max_workers + 1))
        
        # 创建共享的成功和失败文件列表
        shared_success_files = []
        shared_failed_files = []
        # 创建线程锁以保护共享列表
        lock = threading.Lock()
        
        # 创建停止事件用于通知进度更新线程停止
        stop_event = threading.Event()
        
        # 2.启动进度更新线程
        progress_thread = threading.Thread(
            target=update_progress_thread,
            args=(shared_success_files, shared_failed_files, lock, stop_event)
        )
        progress_thread.daemon = True  # 设置为守护线程，主线程结束时自动结束
        progress_thread.start()
        
        # 使用线程池并行上传
        success_count = 0
        failure_count = 0
        success_files, failure_files = [],[]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i in range(max_workers):
                if thread_files[i]:  # 只为有文件的线程创建任务
                    future = executor.submit(
                        upload_task_thread,
                        i,  # thread_id
                        thread_files[i],  # 该线程负责的文件列表
                        thread_sizes[i],   # 该线程负责的文件总大小
                        shared_success_files,  # 共享的成功文件列表
                        shared_failed_files,   # 共享的失败文件列表
                        lock  # 线程锁
                    )
                    futures.append(future)
            
            # 等待所有任务完成
            for future in futures:
                local_success, local_failed = future.result()
                success_count += len(local_success)
                success_files.extend(local_success)
                failure_count += len(local_failed)
                failure_files.extend(local_failed)

        
        # 通知进度更新线程停止
        stop_event.set()
        # 等待进度更新线程完成最后一次更新
        progress_thread.join()
        
        # 由于tqdm进度条会占用终端空间
        # 任务完成后需要打印相同数量的换行来"清理"这些进度条
        # 否则后续输出会紧贴在进度条上
        print("\n" * (max_workers + 1))
        
        # 打印最终结果
        print(f"\n{Fore.GREEN}批量上传完成,上传ID:{self.eai_upload_task_id},可在数采平台-数据管理-SDK上传查看")
        print(f"{Fore.GREEN}成功: {success_count} 个文件")
        if failure_count > 0:
            print(f"{Fore.RED}失败: {failure_count} 个文件，文件列表:{failure_files}")
       
        # 3.通知具身数据平台完成上传
        self.complete_upload_eai_task(status="SUCCESS")

 


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description=__description__)
    
    # 核心参数
    parser.add_argument('-f', '--file', help='要上传的单个文件路径')
    parser.add_argument('-d', '--directory', help='要上传的目录路径')
    parser.add_argument('-s', '--dataset', help='目标数据集路径')
    
    # 功能开关
    parser.add_argument('--direct', action='store_true', help='使用直接认证方式（不使用STS服务）')
    parser.add_argument('--filter', help='文件过滤器，用逗号分隔（例如：*.txt,*.csv）')
    parser.add_argument('--interactive', action='store_true', help='使用交互模式')
    
    return parser.parse_args()


def interactive_mode(use_direct_auth=False):
    """交互模式"""
    show_banner()
    
    # 显示当前配置信息
    # config.print_config_info()
    # print()  # 空行分隔
    
    uploader = RobotDataUploader(use_direct_auth=use_direct_auth)
    
    # 根据用户输入的AK/SK获取金山云ks3的sts
    def get_sts():
        while True:
            ak = input(f"{Fore.BLUE}请输入数采平台Access Key: ")
            if not ak:
                print(f"{Fore.RED}错误: 请输入正确的ak")
                continue
            sk = input(f"{Fore.BLUE}请输入数采平台Secret Key: ")
            if not sk:
                print(f"{Fore.RED}错误: 请输入正确的sk")
                continue
            token = uploader.get_eai_token(ak, sk)
            if not token:
                print(f"{Fore.RED}错误: 认证失败,请输入正确的ak/sk")
                continue
            break
        while True:    
            is_success = uploader.get_ks3_sts()
            if not is_success:
                print(f"{Fore.RED}错误: 获取安全凭证失败，请联系管理员")
                continue
            break    
    
    # 校验任务ID是否存在
    def get_task():
        while True:
            task_id = input(f"{Fore.BLUE}请输入数采平台关联的任务ID {Fore.YELLOW}[可选，回车跳过]: ")
            # 跳过
            if task_id is None or not task_id.strip():
                task_id = -99 
            is_success = uploader.get_eai_task(task_id)
            if not is_success:
                print(f"{Fore.RED}错误: 未检测到有对应的任务ID,请检查")
                continue    
            break
    
    # 校验源文件路径有效性
    def verify_source_file_path():
        while True:
            file_path = input(f"{Fore.BLUE}请输入文件路径: ").strip('"')
            if not os.path.exists(file_path):
                print(f"{Fore.RED}错误：文件不存在 - {file_path}")
                continue
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}错误：路径不是文件 - {file_path}")
                continue
            break
        return file_path
    
    # 校验源目录路径有效性
    def verify_source_dir_path():
        while True:
            directory = input(f"{Fore.BLUE}请输入待上传目录路径: ").strip('"')
            if not os.path.exists(directory):
                print(f"{Fore.RED}错误：目录不存在 - {directory}")
                continue
            if not os.path.isdir(directory):
                print(f"{Fore.RED}错误：路径不是目录 - {directory}")
                continue
            break
        return directory
            
    # 校验目标数据路径有效性
    def verify_target_path():
        while True:
            sub_dir = input(f"{Fore.BLUE}请输入目标数据集路径: ")
            if not sub_dir:
                print(f"{Fore.RED}错误：必须指定目标数据集路径")
                continue
            if not has_any_path_separator(sub_dir):
                print(f"{Fore.RED}错误: 必须至少含有1个路径分隔符'/',如:a/b")
                continue
            break
        return sub_dir
    
    while True:
        show_menu(','.join(uploader.file_filters), '直接认证' if uploader.use_direct_auth else 'STS认证', uploader.max_worker)
        # print(f"\n{Fore.CYAN}请选择操作:")
        # print(f"{Fore.WHITE}1. 上传单个文件")
        # print(f"{Fore.WHITE}2. 上传目录")
        # print(f"{Fore.WHITE}3. 设置文件过滤器 [{Fore.GREEN}当前: { ','.join(uploader.file_filters) }]")
        # print(f"{Fore.WHITE}4. 切换认证方式 [{Fore.GREEN}当前: {'直接认证' if uploader.use_direct_auth else 'STS认证'}]")
        # print(f"{Fore.WHITE}5. 退出")
        
        choice = input(f"{Fore.GREEN}> ")
        if choice == '1':
            get_sts()
            get_task()
            file_path = verify_source_file_path()
            sub_dir = verify_target_path()
            # 上传单个文件
            start_time = time.time()
            uploader.upload_file(file_path, sub_dir)
            end_time = time.time()
            print(f"上传完成，耗时: {end_time - start_time:.2f}秒")
        elif choice == '2':
            get_sts()
            get_task()
            directory = verify_source_dir_path()
            sub_dir = verify_target_path()
            # 批量上传文件
            start_time = time.time()
            uploader.batch_upload(directory, sub_dir)
            end_time = time.time()
            print(f"上传完成，耗时: {end_time - start_time:.2f}秒")
        elif choice == '3':
            filters = input(f"{Fore.BLUE}请输入文件过滤器（用逗号分隔，例如: *.txt,*.csv）: ").split(',')
            uploader.set_file_filters(filters)
            print(f"{Fore.GREEN}文件过滤器已设置为: {', '.join(filters)}")
        elif choice == '4':
            uploader.use_direct_auth = not uploader.use_direct_auth
            uploader.connection = None  # 重置连接
            print(f"{Fore.GREEN}已切换到{'直接认证' if uploader.use_direct_auth else 'STS认证'}方式")
        elif choice == '5':
            while True:
                try:
                    max_worker = input(f"{Fore.BLUE}请输入工作线程数：")
                    max_worker = int(max_worker)
                    import multiprocessing
                    cpu_count = multiprocessing.cpu_count()
                    if max_worker <= 0:
                        print(f"{Fore.RED}错误：工作线程数必须大于0")
                        continue
                    if max_worker > cpu_count:
                        print(f"{Fore.YELLOW}警告：工作线程数超过CPU核心数({cpu_count})，可能影响性能")
                        print(f"{Fore.YELLOW}请重新输入不超过{cpu_count}的线程数")
                        continue
                    uploader.set_max_worker(max_worker)
                    print(f"{Fore.GREEN}工作线程数已设置为: {max_worker}")
                    break
                except ValueError:
                    print(f"{Fore.RED}错误：请输入有效的数字")
        elif choice == '6':
            break
        else:
            print(f"{Fore.RED}无效选择")


def main():
    """主函数"""
    args = parse_arguments()
    
    # 如果没有参数或指定了交互模式，则进入交互模式
    if len(sys.argv) == 1 or args.interactive:
        interactive_mode(use_direct_auth=args.direct)
        return
    
    # 命令行模式
    # 显示当前配置信息
    # config.print_config_info()
    # print()  # 空行分隔
    
    uploader = RobotDataUploader(use_direct_auth=args.direct)
    
    # 设置文件过滤器
    if args.filter:
        uploader.set_file_filters(args.filter.split(','))
    
    # 检查必需参数
    if not args.dataset:
        print(f"{Fore.RED}错误: 必须指定数据集名称 (-s 或 --dataset)")
        sys.exit(1)
    
    # 上传文件或目录
    start_time = time.time()
    if args.file:
        uploader.upload_file(args.file, args.dataset)
    elif args.directory:
        uploader.batch_upload(args.directory, args.dataset)
    end_time = time.time()
    print(f"上传完成，耗时: {end_time - start_time:.2f}秒")


if __name__ == '__main__':
    main() 
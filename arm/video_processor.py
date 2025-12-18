#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一视频处理模块
提供标准化的视频编码和处理功能，避免在多个地方重复实现
"""

import subprocess
from pathlib import Path
from collections import OrderedDict
from typing import Union, Optional


class VideoProcessor:
    """统一视频处理器"""
    
    # 支持的图像格式
    SUPPORTED_IMAGE_EXTS = ['.jpg', '.jpeg', '.png']
    
    @staticmethod
    def detect_image_extension(imgs_dir: Path) -> Optional[str]:
        """
        检测目录中的图片后缀
        
        Args:
            imgs_dir (Path): 图像目录路径
            
        Returns:
            Optional[str]: 图片后缀，如果未找到返回None
        """
        for ext in VideoProcessor.SUPPORTED_IMAGE_EXTS:
            if list(imgs_dir.glob(f"*{ext}")):
                return ext
        return None
    
    @staticmethod
    def encode_rgb_video(
        imgs_dir: Union[Path, str], 
        video_path: Union[Path, str], 
        fps: int, 
        use_gpu: bool = False
    ) -> bool:
        """
        编码RGB视频帧（支持GPU加速）
        
        Args:
            imgs_dir (Union[Path, str]): 图像目录
            video_path (Union[Path, str]): 输出视频路径
            fps (int): 帧率
            use_gpu (bool): 是否使用GPU加速（默认False）
            
        Returns:
            bool: 编码是否成功
        """
        print(f"[INFO] 开始编码RGB视频: {video_path} (GPU: {use_gpu})")
        try:
            imgs_dir = Path(imgs_dir)
            video_path = Path(video_path)
            video_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检测图片后缀
            detected_ext = VideoProcessor.detect_image_extension(imgs_dir)
            if not detected_ext:
                raise ValueError(f"未找到支持的图片文件（支持: {', '.join(VideoProcessor.SUPPORTED_IMAGE_EXTS)}）")
            
            print(f"[DEBUG] 检测到图片后缀: {detected_ext}")
            
            # 构建FFmpeg参数
            ffmpeg_args = OrderedDict([
                ("-f", "image2"),
                ("-r", str(fps)),
                ("-i", str(imgs_dir / f"frame_%06d{detected_ext}")),
                ("-pix_fmt", "yuv420p"),
                ("-g", "5"),
                ("-loglevel", "error"),
            ])
            
            # 使用GPU编码(h264_nvenc)或CPU编码(libx264)
            if use_gpu:
                ffmpeg_args.update([
                    ("-c:v", "h264_nvenc"),
                    ("-preset", "fast"),
                ])
            else:
                ffmpeg_args.update([
                    ("-c:v", "libx264"),
                    ("-crf", "18"),
                ])
            
            ffmpeg_cmd = ["ffmpeg"] + [item for pair in ffmpeg_args.items() for item in pair] + [str(video_path)]
            print(f"[DEBUG] 执行FFmpeg命令: {' '.join(ffmpeg_cmd)}")
            
            result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
            
            if not video_path.exists():
                raise OSError(f"视频文件未生成: {video_path}")
                
            print(f"[INFO] RGB视频编码成功: {video_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] FFmpeg执行失败: {e.stderr}")
            return False
        except Exception as e:
            print(f"[ERROR] RGB视频编码失败: {str(e)}")
            return False
    
    @staticmethod
    def encode_depth_video(
        imgs_dir: Union[Path, str], 
        video_path: Union[Path, str], 
        fps: int
    ) -> bool:
        """
        编码深度视频帧
        
        Args:
            imgs_dir (Union[Path, str]): 图像目录
            video_path (Union[Path, str]): 输出视频路径
            fps (int): 帧率
            
        Returns:
            bool: 编码是否成功
        """
        print(f"[INFO] 开始编码深度视频: {video_path}")
        try:
            imgs_dir = Path(imgs_dir)
            video_path = Path(video_path)
            video_path.parent.mkdir(parents=True, exist_ok=True)

            ffmpeg_args = [
                "ffmpeg",
                "-f", "image2",
                "-r", str(fps),
                "-i", str(imgs_dir / "frame_%06d.png"),
                "-vcodec", "ffv1",
                "-loglevel", "error",
                "-pix_fmt", "gray16le",
                "-y",
                str(video_path)
            ]
            
            print(f"[DEBUG] 执行FFmpeg命令: {' '.join(ffmpeg_args)}")
            result = subprocess.run(ffmpeg_args, check=True, capture_output=True, text=True)
            
            if not video_path.exists():
                raise OSError(f"视频文件未生成: {video_path}")
                
            print(f"[INFO] 深度视频编码成功: {video_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] FFmpeg执行失败: {e.stderr}")
            return False
        except Exception as e:
            print(f"[ERROR] 深度视频编码失败: {str(e)}")
            return False
    
    @staticmethod
    def encode_label_video(
        imgs_dir: Union[Path, str], 
        video_path: Union[Path, str], 
        fps: int
    ) -> bool:
        """
        编码标签视频帧
        
        Args:
            imgs_dir (Union[Path, str]): 图像目录
            video_path (Union[Path, str]): 输出视频路径
            fps (int): 帧率
            
        Returns:
            bool: 编码是否成功
        """
        print(f"[INFO] 开始编码标签视频: {video_path}")
        try:
            imgs_dir = Path(imgs_dir)
            video_path = Path(video_path)
            video_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检测图片后缀
            detected_ext = VideoProcessor.detect_image_extension(imgs_dir)
            if not detected_ext:
                raise ValueError(f"未找到支持的图片文件（支持: {', '.join(VideoProcessor.SUPPORTED_IMAGE_EXTS)}）")
            
            print(f"[DEBUG] 检测到图片后缀: {detected_ext}")

            ffmpeg_args = OrderedDict([
                ("-f", "image2"),
                ("-r", str(fps)),
                ("-i", str(imgs_dir / f"frame_%06d{detected_ext}")),
                ("-vcodec", "libx264"),
                ("-pix_fmt", "yuv420p"),
                ("-g", "20"),
                ("-crf", "23"),
                ("-loglevel", "error"),
            ])

            ffmpeg_cmd = ["ffmpeg"] + [item for pair in ffmpeg_args.items() for item in pair] + [str(video_path)]
            print(f"[DEBUG] 执行FFmpeg命令: {' '.join(ffmpeg_cmd)}")
            
            result = subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
            
            if not video_path.exists():
                raise OSError(f"视频文件未生成: {video_path}")
                
            print(f"[INFO] 标签视频编码成功: {video_path}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] FFmpeg执行失败: {e.stderr}")
            return False
        except Exception as e:
            print(f"[ERROR] 标签视频编码失败: {str(e)}")
            return False


# 为了向后兼容，保留原来的函数名
def encode_video_frames(imgs_dir: Union[Path, str], video_path: Union[Path, str], fps: int, use_gpu: bool = False) -> bool:
    """向后兼容的RGB视频编码函数"""
    return VideoProcessor.encode_rgb_video(imgs_dir, video_path, fps, use_gpu)


def encode_depth_video_frames(imgs_dir: Union[Path, str], video_path: Union[Path, str], fps: int) -> bool:
    """向后兼容的深度视频编码函数"""
    return VideoProcessor.encode_depth_video(imgs_dir, video_path, fps)


def encode_label_video_frames(imgs_dir: Union[Path, str], video_path: Union[Path, str], fps: int) -> bool:
    """向后兼容的标签视频编码函数"""
    return VideoProcessor.encode_label_video(imgs_dir, video_path, fps)

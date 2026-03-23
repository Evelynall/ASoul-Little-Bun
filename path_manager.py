"""
路径管理模块
提供统一的程序路径管理，确保无论从哪个目录启动程序都能正确找到文件
"""
import os
import sys


class PathManager:
    """路径管理器，统一管理程序中所有文件路径"""

    def __init__(self):
        # 获取程序根目录
        if getattr(sys, 'frozen', False):
            # 打包后的exe文件所在目录
            self.base_dir = os.path.dirname(sys.executable)
        else:
            # Python脚本所在目录
            self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # 确保路径使用正斜杠（避免Windows路径问题）
        self.base_dir = self.base_dir.replace('\\', '/')

    def get_path(self, *path_parts):
        """
        获取相对于程序根目录的绝对路径

        Args:
            *path_parts: 路径部分，例如 'config', 'settings.json'

        Returns:
            str: 绝对路径
        """
        return os.path.join(self.base_dir, *path_parts).replace('\\', '/')

    def exists(self, *path_parts):
        """
        检查文件或目录是否存在

        Args:
            *path_parts: 路径部分

        Returns:
            bool: 是否存在
        """
        return os.path.exists(self.get_path(*path_parts))

    def get_version_file(self):
        """获取version.json文件路径"""
        return self.get_path('version.json')

    def get_global_config_file(self):
        """获取全局配置文件路径"""
        return self.get_path('global_config.json')

    def get_img_dir(self):
        """获取img目录路径"""
        return self.get_path('img')

    def get_character_dir(self, character_name):
        """
        获取角色目录路径

        Args:
            character_name: 角色名称

        Returns:
            str: 角色目录的绝对路径
        """
        return self.get_path('img', character_name)

    def get_character_config(self, character_name):
        """
        获取角色配置文件路径

        Args:
            character_name: 角色名称

        Returns:
            str: 角色配置文件的绝对路径
        """
        return self.get_path('img', character_name, 'config.json')

    def get_custom_layers_file(self, character_name=None):
        """
        获取自定义图层配置文件路径

        Args:
            character_name: 角色名称（可选）。如果提供，使用角色的custom_layers.json；
                          如果不提供，使用全局custom_layers.json

        Returns:
            str: 自定义图层配置文件的绝对路径
        """
        if character_name:
            return self.get_path('img', character_name, 'custom_layers.json')
        else:
            return self.get_path('img', 'custom_layers.json')

    def get_changelogs_dir(self):
        """获取changelogs目录路径"""
        return self.get_path('changelogs')

    def get_base_dir(self):
        """获取程序根目录"""
        return self.base_dir


# 创建全局路径管理器实例
path_manager = PathManager()

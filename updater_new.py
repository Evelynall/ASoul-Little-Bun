"""
自动更新程序（新版）
用于下载和替换主程序文件
支持配置文件合并策略：已有键保留用户值，只新增缺失的键
支持自我更新（通过延迟替换脚本）
启动后会自动清理旧版 updater.exe
"""
import sys
import os
import time
import json
import zipfile
import shutil
import subprocess
from pathlib import Path

# Windows下使用msvcrt来实现按任意键
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


def get_base_dir():
    """获取程序根目录"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.resolve()


# ============================================================
# 配置文件合并策略
# ============================================================

# 需要使用合并策略的配置文件名
MERGE_CONFIG_FILES = {'config.json', 'global_config.json', 'custom_layers.json'}


def deep_merge(user_data, new_data):
    """
    深度合并两个字典：保留 user_data 中已有的键值，只新增 new_data 中缺失的键。
    对于嵌套字典会递归合并；对于非字典值，以 user_data 为准。
    
    Args:
        user_data: 用户现有的配置（优先级高）
        new_data: 新版本带来的配置（仅补充缺失键）
    
    Returns:
        合并后的字典
    """
    if not isinstance(user_data, dict) or not isinstance(new_data, dict):
        # 如果其中一个不是字典，保留用户值
        return user_data
    
    merged = dict(user_data)  # 以用户数据为基础
    for key, new_value in new_data.items():
        if key not in merged:
            # 用户数据中没有这个键 → 使用新值
            merged[key] = new_value
        elif isinstance(merged[key], dict) and isinstance(new_value, dict):
            # 双方都是字典 → 递归合并
            merged[key] = deep_merge(merged[key], new_value)
        # 否则保留用户已有的值，不覆盖
    
    return merged


def merge_custom_layers(user_layers, new_layers):
    """
    合并 custom_layers.json 数组：按 name 字段去重，保留用户已有的图层配置，
    只新增新版本中不存在的图层。
    
    Args:
        user_layers: 用户现有的图层列表
        new_layers: 新版本带来的图层列表
    
    Returns:
        合并后的图层列表
    """
    if not isinstance(user_layers, list):
        user_layers = []
    if not isinstance(new_layers, list):
        new_layers = []
    
    # 以用户数据为基础，按 name 索引已有图层
    user_by_name = {}
    for layer in user_layers:
        if isinstance(layer, dict) and 'name' in layer:
            user_by_name[layer['name']] = layer
    
    # 添加新版本中用户没有的图层
    for layer in new_layers:
        if isinstance(layer, dict) and 'name' in layer:
            if layer['name'] not in user_by_name:
                user_layers.append(layer)
        else:
            # 没有name字段的图层直接追加（如果不存在）
            if layer not in user_layers:
                user_layers.append(layer)
    
    return user_layers


def merge_config_file(user_file, new_file, filename):
    """
    根据文件类型选择合适的合并策略，合并配置文件。
    
    Args:
        user_file: 用户现有的配置文件路径
        new_file: 新版本的配置文件路径
        filename: 配置文件名（用于选择合并策略）
    
    Returns:
        合并后的数据（dict 或 list），如果合并失败返回 None
    """
    try:
        # 读取用户现有配置
        if user_file.exists():
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
        else:
            user_data = None
        
        # 读取新版本配置
        with open(new_file, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        
        if user_data is None:
            # 用户没有配置文件 → 直接使用新版本
            return new_data
        
        if filename == 'custom_layers.json':
            # custom_layers.json 是数组，使用专用合并
            return merge_custom_layers(user_data, new_data)
        else:
            # config.json / global_config.json 是字典，使用深度合并
            return deep_merge(user_data, new_data)
            
    except Exception as e:
        print(f"合并配置文件 {filename} 失败: {e}")
        return None


# ============================================================
# 更新器
# ============================================================


class Updater:
    def __init__(self, zip_path):
        """
        初始化更新器
        Args:
            zip_path: 已下载的zip文件路径
        """
        self.zip_path = Path(zip_path)
        # 使用程序根目录作为临时目录的基础
        self.base_dir = get_base_dir()
        self.temp_dir = self.base_dir / "temp_update"
        # 标记是否需要延迟自我更新（cleanup 时需要保留解压目录）
        self.pending_self_update = False
        
    def extract_update(self):
        """解压更新文件"""
        try:
            print("正在解压文件...")
            extract_dir = self.temp_dir / "extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print("解压完成！")
            return extract_dir
            
        except Exception as e:
            print(f"解压失败: {e}")
            return None
    
    def replace_files(self, extract_dir):
        """替换文件，对配置文件使用智能合并策略，支持 updater_new 自更新"""
        try:
            print("正在替换文件...")
            current_dir = Path.cwd()
            
            # 获取解压后的根目录（可能有一层文件夹）
            extracted_items = list(extract_dir.iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
            else:
                source_dir = extract_dir
            
            # 备份当前程序
            backup_dir = Path("backup_before_update")
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            backup_dir.mkdir(exist_ok=True)
            
            # 获取当前 updater 的文件名（updater_new.exe 或 updater_new.py）
            if getattr(sys, 'frozen', False):
                updater_name = Path(sys.executable).name  # updater_new.exe
            else:
                updater_name = Path(__file__).name  # updater_new.py
            
            # 延迟替换：新版 updater 的源文件路径
            pending_updater_source = None
            
            # 需要替换的文件列表
            files_to_update = []
            for item in source_dir.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(source_dir)
                    files_to_update.append(rel_path)
            
            # 备份并替换文件
            for rel_path in files_to_update:
                source_file = source_dir / rel_path
                target_file = current_dir / rel_path
                backup_file = backup_dir / rel_path
                
                # 跳过临时目录
                if 'temp_update' in rel_path.parts or 'backup_before_update' in rel_path.parts:
                    continue
                
                # 跳过旧版 updater.exe / updater.py（不替换旧版，稍后统一清理）
                if rel_path.name in ('updater.exe', 'updater.py'):
                    print(f"跳过旧版更新程序: {rel_path.name}（稍后清理）")
                    continue
                
                # updater_new 自身：记录下来，稍后延迟替换
                if rel_path.name == updater_name:
                    print(f"检测到新版更新程序，将在所有文件替换完成后进行自我更新")
                    pending_updater_source = source_file
                    # 先备份当前 updater
                    if target_file.exists():
                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            shutil.copy2(target_file, backup_file)
                        except:
                            pass
                    continue
                
                # 备份原文件
                if target_file.exists():
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(target_file, backup_file)
                    except:
                        pass  # 如果备份失败也继续
                
                # 配置文件使用合并策略
                if rel_path.name in MERGE_CONFIG_FILES:
                    merged_data = merge_config_file(target_file, source_file, rel_path.name)
                    if merged_data is not None:
                        try:
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(target_file, 'w', encoding='utf-8') as f:
                                json.dump(merged_data, f, indent=4, ensure_ascii=False)
                            print(f"已合并更新: {rel_path}")
                        except Exception as e:
                            print(f"合并写入失败 {rel_path}: {e}")
                    else:
                        # 合并失败，回退到直接复制
                        try:
                            target_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(source_file, target_file)
                            print(f"合并失败，已直接覆盖: {rel_path}")
                        except Exception as e:
                            print(f"更新失败 {rel_path}: {e}")
                else:
                    # 非配置文件直接复制
                    try:
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_file, target_file)
                        print(f"已更新: {rel_path}")
                    except Exception as e:
                        print(f"更新失败 {rel_path}: {e}")
            
            # 所有其他文件替换完成后，执行 updater 自更新
            if pending_updater_source and pending_updater_source.exists():
                self.pending_self_update = True
                self._self_update(pending_updater_source, current_dir, updater_name)
            
            # 清理旧版 updater.exe / updater.py（如果存在）
            self._cleanup_old_updater(current_dir)
            
            print("文件替换完成！")
            return True
            
        except Exception as e:
            print(f"替换文件失败: {e}")
            return False
    
    def _cleanup_old_updater(self, current_dir):
        """
        清理旧版 updater.exe / updater.py。
        旧版更新程序无法自我更新到新版，因此新版启动后主动删除旧版文件。
        """
        old_files = ['updater.exe', 'updater.py']
        for name in old_files:
            old_path = current_dir / name
            if old_path.exists():
                try:
                    os.remove(old_path)
                    print(f"已清理旧版更新程序: {name}")
                except Exception as e:
                    print(f"清理旧版更新程序 {name} 失败: {e}")

    def _self_update(self, new_updater_path, current_dir, updater_name):
        """
        延迟自我更新：创建一个 bat 脚本，在当前 updater 退出后替换自身。
        
        原理：Windows 锁定正在运行的 exe，无法直接覆盖。
        通过 bat 脚本等待当前进程退出后再执行替换，完美规避锁定问题。
        """
        try:
            target_updater = current_dir / updater_name
            bat_path = current_dir / "_update_updater.bat"
            updater_pid = os.getpid()
            
            # 构建 bat 脚本内容
            # 使用 ping 实现等待（避免 timeout 命令在某些 Windows 版本上不可用）
            # Path 对象转为 str 确保使用系统路径分隔符
            temp_dir_str = str(self.temp_dir).replace('/', '\\')
            bat_content = f"""@echo off
chcp 65001 >nul 2>&1
echo 正在等待更新程序退出...
:wait_loop
tasklist /FI "PID eq {updater_pid}" 2>nul | find /I "{updater_pid}" >nul
if not errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto wait_loop
)
echo 正在替换更新程序...
copy /Y "{new_updater_path}" "{target_updater}" >nul 2>&1
if errorlevel 1 (
    echo 自我更新失败，请手动更新 updater
    ping -n 3 127.0.0.1 >nul
)
del /F "{new_updater_path}" >nul 2>&1
if exist "{temp_dir_str}" rmdir /S /Q "{temp_dir_str}" >nul 2>&1
del /F "%~f0" >nul 2>&1
"""
            
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            # 启动 bat 脚本（独立窗口、最小化运行）
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 6  # SW_MINIMIZE
            subprocess.Popen(
                ['cmd', '/c', str(bat_path)],
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            print(f"已安排更新程序自我更新（通过延迟替换）")
            
        except Exception as e:
            print(f"更新程序自我更新失败: {e}")
            # 回退：尝试直接覆盖（PyInstaller 单文件模式通常可以）
            try:
                shutil.copy2(new_updater_path, current_dir / updater_name)
                print("已直接覆盖更新程序（回退方案）")
            except Exception as e2:
                print(f"直接覆盖也失败: {e2}，将在下次更新时重试")
    
    def cleanup(self):
        """清理临时文件（如果有延迟自更新则保留解压目录，由 bat 脚本清理）"""
        try:
            if self.pending_self_update:
                # 延迟自更新中，不能删除解压目录（bat 脚本还需要从中复制 updater）
                # bat 脚本会自行清理新版 updater 源文件
                print("延迟自更新中，保留临时目录（由辅助脚本清理）")
            elif self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                print("清理完成！")
        except Exception as e:
            print(f"清理失败: {e}")
    
    def run_update(self):
        """执行完整的更新流程"""
        try:
            # 解压
            extract_dir = self.extract_update()
            if not extract_dir:
                return False
            
            # 替换文件
            if not self.replace_files(extract_dir):
                return False
            
            # 清理
            self.cleanup()
            
            return True
            
        except Exception as e:
            print(f"更新失败: {e}")
            return False


def wait_for_key():
    """等待用户按键"""
    if HAS_MSVCRT:
        # Windows系统使用msvcrt
        print("按任意键退出...")
        msvcrt.getch()
    else:
        # 其他系统使用input
        input("按Enter键退出...")


def main():
    """主函数 - 命令行模式"""
    if len(sys.argv) < 2:
        print("用法: python updater.py <zip文件路径> [主程序路径]")
        wait_for_key()
        sys.exit(1)
    
    zip_path = sys.argv[1]
    main_program = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("=" * 50)
    print("ASoul Little Bun 自动更新程序")
    print("=" * 50)
    
    # 等待主程序关闭
    if main_program:
        print("等待主程序关闭...")
        time.sleep(2)
    
    # 执行更新
    updater = Updater(zip_path)
    
    if updater.run_update():
        print("\n更新成功！")
        
        # 重启主程序
        if main_program and os.path.exists(main_program):
            print(f"正在重启程序: {main_program}")
            time.sleep(1)
            
            # 判断是exe还是py文件
            if main_program.endswith('.exe'):
                # 直接运行exe
                subprocess.Popen([main_program])
            elif main_program.endswith('.py'):
                # 使用Python运行py文件
                subprocess.Popen([sys.executable, main_program])
            else:
                # 尝试直接运行
                try:
                    subprocess.Popen([main_program])
                except:
                    print(f"无法启动程序: {main_program}")
        
        wait_for_key()
        sys.exit(0)
    else:
        print("\n更新失败！")
        wait_for_key()
        sys.exit(1)


if __name__ == "__main__":
    main()

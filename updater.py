"""
自动更新程序
用于下载和替换主程序文件
"""
import sys
import os
import time
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


class Updater:
    def __init__(self, zip_path):
        """
        初始化更新器
        Args:
            zip_path: 已下载的zip文件路径
        """
        self.zip_path = Path(zip_path)
        self.temp_dir = Path("temp_update")
        
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
        """替换文件"""
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
                
                # 跳过某些文件
                if rel_path.name in ['global_config.json', 'updater.py', 'temp_update']:
                    continue
                
                # 跳过配置文件夹
                if 'temp_update' in rel_path.parts or 'backup_before_update' in rel_path.parts:
                    continue
                
                # 备份原文件
                if target_file.exists():
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(target_file, backup_file)
                    except:
                        pass  # 如果备份失败也继续
                
                # 复制新文件
                try:
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
                    print(f"已更新: {rel_path}")
                except Exception as e:
                    print(f"更新失败 {rel_path}: {e}")
            
            print("文件替换完成！")
            return True
            
        except Exception as e:
            print(f"替换文件失败: {e}")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        try:
            if self.temp_dir.exists():
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

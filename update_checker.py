import json
import requests
import os
import shutil
import sys
import subprocess
from PyQt6.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, QTextBrowser, 
                              QPushButton, QHBoxLayout, QProgressBar, QLabel, QWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from packaging import version as pkg_version


class UpdateCheckThread(QThread):
    """异步更新检查线程"""
    update_found = pyqtSignal(str, str, list, str)  # 当前版本, 最新版本, 更新日志, 下载链接
    check_failed = pyqtSignal()
    
    def __init__(self, checker, local_version, global_settings):
        super().__init__()
        self.checker = checker
        self.local_version = local_version
        self.global_settings = global_settings
    
    def run(self):
        """在后台线程中执行更新检查"""
        try:
            remote_version, download_url = self.checker.get_remote_version()
            
            if remote_version is None:
                self.check_failed.emit()
                return
            
            # 检查是否跳过此版本
            if self.global_settings:
                skipped_version = self.global_settings.get('skipped_update_version')
                if skipped_version == remote_version:
                    print(f"ℹ️ 已跳过版本 {remote_version} 的更新提示")
                    return
            
            # 比较版本
            if pkg_version.parse(remote_version) > pkg_version.parse(self.local_version):
                # 获取更新日志
                changelogs = self.checker.get_changelogs_between_versions(
                    self.local_version, remote_version
                )
                self.update_found.emit(self.local_version, remote_version, changelogs, download_url)
        except Exception as e:
            print(f"更新检查线程异常: {e}")
            self.check_failed.emit()


class DownloadThread(QThread):
    """下载更新线程"""
    progress = pyqtSignal(int)  # 下载进度
    finished = pyqtSignal(bool, str)  # 完成信号 (成功, 消息)
    
    def __init__(self, download_url, proxy_url):
        super().__init__()
        self.download_url = download_url
        self.proxy_url = proxy_url
    
    def run(self):
        """执行下载"""
        try:
            # 使用加速链接
            if self.download_url.startswith("https://github.com"):
                url = f"{self.proxy_url}{self.download_url}"
            else:
                url = self.download_url
            
            # 下载文件
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 保存到临时文件
            temp_dir = "temp_update"
            os.makedirs(temp_dir, exist_ok=True)
            zip_path = os.path.join(temp_dir, "update.zip")
            
            downloaded = 0
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            self.progress.emit(progress)
            
            self.finished.emit(True, zip_path)
            
        except Exception as e:
            self.finished.emit(False, str(e))


class UpdateChecker:
    def __init__(self):
        self.proxy_url = "https://gh-proxy.com/"
        self.repo_url = "https://github.com/Evelynall/ASoul-Little-Bun"
        self.github_release_url = "https://github.com/Evelynall/ASoul-Little-Bun/releases/"
        self.lanzou_url = "https://evelynal.lanzoum.com/b0j1b6kdg"
        self.lanzou_password = "asoul"
        self.check_thread = None
        
    def get_local_version(self):
        """获取本地版本号"""
        try:
            with open('version.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        except Exception as e:
            print(f"读取本地版本失败: {e}")
            return '1.0.0'
    
    def get_remote_version(self):
        """通过加速链接获取远程版本号和下载链接"""
        try:
            # 使用加速链接访问 GitHub raw 文件
            raw_url = f"{self.proxy_url}https://raw.githubusercontent.com/Evelynall/ASoul-Little-Bun/main/version.json"
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            version = data.get('version', '1.0.0')
            download_url = data.get('download_url', '')
            return version, download_url
        except Exception as e:
            print(f"获取远程版本失败: {e}")
            return None, None
    
    def get_changelogs_between_versions(self, current_ver, latest_ver):
        """获取两个版本之间的所有更新日志"""
        changelogs = []
        try:
            # 方法1: 尝试直接访问 GitHub API（不使用代理）
            api_url = "https://api.github.com/repos/Evelynall/ASoul-Little-Bun/contents/changelogs"
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'ASoul-Little-Bun-Updater'
            }
            
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                response.raise_for_status()
                files = response.json()
            except Exception as e:
                print(f"GitHub API 访问失败: {e}")
                # 方法2: 使用加速链接访问 raw 文件（逐个尝试已知版本）
                return self._get_changelogs_by_raw_files(current_ver, latest_ver)
            
            # 筛选出版本号大于当前版本的更新日志
            for file in files:
                if file['name'].endswith('.md'):
                    # 从文件名提取版本号 (例如: v1.0.0.md -> 1.0.0)
                    file_version = file['name'].replace('v', '').replace('.md', '')
                    try:
                        if pkg_version.parse(file_version) > pkg_version.parse(current_ver):
                            # 获取更新日志内容 - 优先使用加速链接
                            content_url = f"{self.proxy_url}{file['download_url']}"
                            try:
                                content_response = requests.get(content_url, timeout=10)
                                content_response.raise_for_status()
                                content = content_response.text
                            except:
                                # 如果加速链接失败，直接访问 GitHub
                                content_response = requests.get(file['download_url'], timeout=10)
                                content_response.raise_for_status()
                                content = content_response.text
                            
                            changelogs.append({
                                'version': file_version,
                                'content': content
                            })
                    except Exception as e:
                        print(f"解析版本 {file_version} 失败: {e}")
                        continue
            
            # 按版本号排序
            changelogs.sort(key=lambda x: pkg_version.parse(x['version']))
            return changelogs
            
        except Exception as e:
            print(f"获取更新日志失败: {e}")
            return []
    
    def _get_changelogs_by_raw_files(self, current_ver, latest_ver):
        """备用方法：通过 raw 文件直接获取更新日志"""
        changelogs = []
        try:
            # 生成可能的版本号列表（从当前版本到最新版本）
            current_parts = [int(x) for x in current_ver.split('.')]
            latest_parts = [int(x) for x in latest_ver.split('.')]
            
            # 简单策略：尝试获取一些常见的版本号
            versions_to_try = []
            
            # 生成从当前版本到最新版本之间的可能版本
            for major in range(current_parts[0], latest_parts[0] + 1):
                for minor in range(0, 20):  # 假设次版本号不超过20
                    for patch in range(0, 20):  # 假设修订号不超过20
                        version_str = f"{major}.{minor}.{patch}"
                        try:
                            if pkg_version.parse(version_str) > pkg_version.parse(current_ver) and \
                               pkg_version.parse(version_str) <= pkg_version.parse(latest_ver):
                                versions_to_try.append(version_str)
                        except:
                            continue
            
            # 尝试获取这些版本的更新日志
            for version in versions_to_try[:10]:  # 限制最多尝试10个版本
                raw_url = f"{self.proxy_url}https://raw.githubusercontent.com/Evelynall/ASoul-Little-Bun/main/changelogs/v{version}.md"
                try:
                    response = requests.get(raw_url, timeout=5)
                    if response.status_code == 200:
                        changelogs.append({
                            'version': version,
                            'content': response.text
                        })
                except:
                    continue
            
            # 按版本号排序
            changelogs.sort(key=lambda x: pkg_version.parse(x['version']))
            return changelogs
            
        except Exception as e:
            print(f"备用方法获取更新日志失败: {e}")
            return []
    
    def check_for_updates(self, parent=None, global_settings=None):
        """异步检查更新（不阻塞UI）"""
        local_version = self.get_local_version()
        
        # 创建后台线程进行更新检查
        self.check_thread = UpdateCheckThread(self, local_version, global_settings)
        
        # 连接信号
        self.check_thread.update_found.connect(
            lambda current, latest, logs, url: self.show_update_dialog(
                current, latest, logs, url, parent, global_settings
            )
        )
        self.check_thread.check_failed.connect(
            lambda: print("更新检查失败或无需更新")
        )
        
        # 启动线程
        self.check_thread.start()
    
    def show_update_dialog(self, current_ver, latest_ver, changelogs, download_url, parent=None, global_settings=None):
        """显示更新对话框"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("发现新版本")
        dialog.setMinimumSize(600, 500)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        # 保存下载线程引用，避免被垃圾回收
        dialog.download_thread = None
        
        layout = QVBoxLayout()
        
        # 版本信息
        info_text = f"<h2>发现新版本！</h2>"
        info_text += f"<p><b>当前版本：</b>{current_ver}</p>"
        info_text += f"<p><b>最新版本：</b>{latest_ver}</p>"
        info_text += f"<hr>"
        
        # 更新日志
        changelog_text = ""
        if changelogs:
            for log in changelogs:
                changelog_text += f"<h3>版本 {log['version']}</h3>"
                # 将 Markdown 转换为简单的 HTML
                content = log['content'].replace('\n', '<br>')
                changelog_text += f"<div>{content}</div><hr>"
        else:
            changelog_text = "<p>无法获取更新日志</p>"
        
        # 文本浏览器显示更新内容
        text_browser = QTextBrowser()
        text_browser.setHtml(info_text + changelog_text)
        text_browser.setOpenExternalLinks(True)
        layout.addWidget(text_browser)
        
        # 下载地址信息
        download_info = QTextBrowser()
        download_info.setMaximumHeight(100)
        download_html = "<h3>下载地址：</h3>"
        download_html += f"<p><b>GitHub：</b><a href='{self.github_release_url}'>{self.github_release_url}</a></p>"
        download_html += f"<p><b>蓝奏云：</b><a href='{self.lanzou_url}'>{self.lanzou_url}</a> (密码: {self.lanzou_password})</p>"
        download_info.setHtml(download_html)
        download_info.setOpenExternalLinks(True)
        layout.addWidget(download_info)
        
        # 进度条（初始隐藏）
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_label = QLabel("准备下载...")
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(progress_bar)
        progress_widget.setVisible(False)
        layout.addWidget(progress_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        # 自动下载按钮
        auto_update_btn = QPushButton("自动下载更新")
        auto_update_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        
        def start_download():
            """开始下载"""
            if not download_url:
                QMessageBox.warning(dialog, "错误", "未找到下载链接，请手动下载")
                return
            
            # 禁用按钮
            auto_update_btn.setEnabled(False)
            manual_btn.setEnabled(False)
            skip_btn.setEnabled(False)
            later_btn.setEnabled(False)
            
            # 显示进度条
            progress_widget.setVisible(True)
            progress_label.setText("正在下载更新...")
            
            # 创建下载线程并保存引用
            dialog.download_thread = DownloadThread(download_url, self.proxy_url)
            
            def on_progress(value):
                progress_bar.setValue(value)
                progress_label.setText(f"正在下载更新... {value}%")
            
            def on_finished(success, result):
                if success:
                    progress_label.setText("下载完成！准备安装...")
                    # 启动更新程序
                    self.launch_updater(result, dialog)
                else:
                    progress_label.setText(f"下载失败: {result}")
                    QMessageBox.critical(dialog, "下载失败", f"下载更新失败：{result}\n\n请尝试手动下载")
                    # 恢复按钮
                    auto_update_btn.setEnabled(True)
                    manual_btn.setEnabled(True)
                    skip_btn.setEnabled(True)
                    later_btn.setEnabled(True)
                    progress_widget.setVisible(False)
            
            dialog.download_thread.progress.connect(on_progress)
            dialog.download_thread.finished.connect(on_finished)
            dialog.download_thread.start()
        
        auto_update_btn.clicked.connect(start_download)
        
        manual_btn = QPushButton("手动下载")
        manual_btn.clicked.connect(lambda: self.open_download_page())
        manual_btn.clicked.connect(dialog.accept)
        
        skip_btn = QPushButton("跳过此版本")
        skip_btn.clicked.connect(lambda: self.skip_version(latest_ver, global_settings, dialog))
        
        later_btn = QPushButton("稍后提醒")
        later_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(auto_update_btn)
        button_layout.addWidget(manual_btn)
        button_layout.addWidget(skip_btn)
        button_layout.addWidget(later_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        # 对话框关闭时清理线程
        def cleanup():
            if dialog.download_thread and dialog.download_thread.isRunning():
                dialog.download_thread.wait(1000)  # 等待最多1秒
        
        dialog.finished.connect(cleanup)
        dialog.exec()
    
    def skip_version(self, version, global_settings, dialog):
        """跳过指定版本的更新"""
        if global_settings:
            global_settings.set('skipped_update_version', version)
            global_settings.save()
            print(f"✅ 已跳过版本 {version} 的更新提示")
        dialog.reject()
    
    def open_download_page(self):
        """打开下载页面"""
        import webbrowser
        webbrowser.open(self.github_release_url)
    
    def launch_updater(self, zip_path, dialog):
        """启动更新程序"""
        try:
            # 获取当前程序路径
            if getattr(sys, 'frozen', False):
                # 打包后的exe
                current_exe = sys.executable
                current_dir = os.path.dirname(current_exe)
            else:
                # Python脚本 - 使用main.py
                current_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))
                current_dir = os.path.dirname(__file__)
            
            # 优先查找updater.exe
            updater_exe = os.path.join(current_dir, 'updater.exe')
            updater_script = os.path.join(current_dir, 'updater.py')
            
            # 如果是打包模式且updater.exe不存在，尝试从临时目录提取
            if getattr(sys, 'frozen', False) and not os.path.exists(updater_exe):
                if hasattr(sys, '_MEIPASS'):
                    temp_updater = os.path.join(sys._MEIPASS, 'updater.exe')
                    if os.path.exists(temp_updater):
                        import shutil
                        shutil.copy2(temp_updater, updater_exe)
                        print(f"已提取updater.exe到: {updater_exe}")
            
            # 确定使用哪个更新程序
            use_exe = os.path.exists(updater_exe)
            use_script = os.path.exists(updater_script)
            
            if not use_exe and not use_script:
                QMessageBox.warning(dialog, "错误", 
                    "未找到更新程序！\n\n"
                    "请确保updater.exe或updater.py与程序在同一目录")
                return
            
            # 显示确认对话框
            updater_type = "updater.exe" if use_exe else "updater.py (需要Python)"
            reply = QMessageBox.question(
                dialog, 
                "确认更新", 
                f"下载完成！\n\n"
                f"将使用 {updater_type} 进行更新\n"
                f"更新程序将关闭当前程序并自动安装更新。\n\n是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 启动更新程序
                if use_exe:
                    # 使用exe版本（无需Python）
                    subprocess.Popen([updater_exe, zip_path, current_exe])
                else:
                    # 使用Python脚本版本
                    try:
                        subprocess.Popen([sys.executable, updater_script, zip_path, current_exe])
                    except:
                        try:
                            subprocess.Popen(['python', updater_script, zip_path, current_exe])
                        except:
                            QMessageBox.critical(dialog, "错误", 
                                "无法启动更新程序！\n\n"
                                "请确保系统已安装Python")
                            return
                
                # 关闭主程序
                dialog.accept()
                QMessageBox.information(dialog, "更新中", "更新程序已启动，主程序即将关闭...")
                sys.exit(0)
            
        except Exception as e:
            QMessageBox.critical(dialog, "错误", f"启动更新程序失败：{e}")

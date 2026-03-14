import json
import requests
import os
import shutil
from PyQt6.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from packaging import version as pkg_version


class UpdateChecker:
    def __init__(self):
        self.proxy_url = "https://gh-proxy.com/"
        self.repo_url = "https://github.com/Evelynall/ASoul-Little-Bun"
        self.github_release_url = "https://github.com/Evelynall/ASoul-Little-Bun/releases/"
        self.lanzou_url = "https://evelynal.lanzoum.com/b0j1b6kdg"
        self.lanzou_password = "asoul"
        self.changelogs_dir = "changelogs"  # 本地更新日志目录
    
    def clean_local_changelogs(self):
        """清理本地更新日志文件夹"""
        try:
            if os.path.exists(self.changelogs_dir):
                shutil.rmtree(self.changelogs_dir)
                print(f"✅ 已清理本地更新日志: {self.changelogs_dir}")
            else:
                print(f"ℹ️ 本地更新日志目录不存在，无需清理")
        except Exception as e:
            print(f"⚠️ 清理本地更新日志失败: {e}")
        
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
        """通过加速链接获取远程版本号"""
        try:
            # 使用加速链接访问 GitHub raw 文件
            raw_url = f"{self.proxy_url}https://raw.githubusercontent.com/Evelynall/ASoul-Little-Bun/main/version.json"
            response = requests.get(raw_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('version', '1.0.0')
        except Exception as e:
            print(f"获取远程版本失败: {e}")
            return None
    
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
        """检查更新并显示对话框"""
        local_version = self.get_local_version()
        remote_version = self.get_remote_version()
        
        if remote_version is None:
            return False
        
        try:
            if pkg_version.parse(remote_version) > pkg_version.parse(local_version):
                # 检查是否跳过此版本
                if global_settings:
                    skipped_version = global_settings.get('skipped_update_version')
                    if skipped_version == remote_version:
                        print(f"ℹ️ 已跳过版本 {remote_version} 的更新提示")
                        return False
                
                # 获取更新日志
                changelogs = self.get_changelogs_between_versions(local_version, remote_version)
                
                # 显示更新对话框
                self.show_update_dialog(local_version, remote_version, changelogs, parent, global_settings)
                return True
            else:
                return False
        except Exception as e:
            print(f"版本比较失败: {e}")
            return False
    
    def show_update_dialog(self, current_ver, latest_ver, changelogs, parent=None, global_settings=None):
        """显示更新对话框"""
        dialog = QDialog(parent)
        dialog.setWindowTitle("发现新版本")
        dialog.setMinimumSize(600, 400)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
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
        
        # 按钮
        button_layout = QHBoxLayout()
        
        update_btn = QPushButton("前往下载")
        update_btn.clicked.connect(lambda: self.open_download_page())
        update_btn.clicked.connect(dialog.accept)
        
        skip_btn = QPushButton("跳过此版本")
        skip_btn.clicked.connect(lambda: self.skip_version(latest_ver, global_settings, dialog))
        
        later_btn = QPushButton("稍后提醒")
        later_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(update_btn)
        button_layout.addWidget(skip_btn)
        button_layout.addWidget(later_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
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

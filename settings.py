import json
import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QSpinBox, QPushButton, QGroupBox, QFormLayout,
                              QSlider, QScrollArea, QWidget, QApplication, QCheckBox, QTabWidget)
from PyQt6.QtCore import Qt
from path_manager import path_manager


class GlobalSettings:
    """全局设置管理类"""
    DEFAULT_SETTINGS = {
        'window_x': 0,
        'window_y': 0,
        'last_character': None
    }
    
    def __init__(self, config_file='global_config.json'):
        # 使用路径管理器获取绝对路径
        if not os.path.isabs(config_file):
            self.config_file = path_manager.get_global_config_file()
        else:
            self.config_file = config_file
        self.settings = self.load()
    
    def load(self):
        """加载全局设置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    return settings
            except Exception as e:
                print(f"加载全局设置失败: {e}")
                return self.DEFAULT_SETTINGS.copy()
        return self.DEFAULT_SETTINGS.copy()
    
    def save(self):
        """保存全局设置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存全局设置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置值"""
        self.settings[key] = value
    
    @staticmethod
    def get_startup_folder():
        """获取Windows启动文件夹路径"""
        try:
            from win32com.shell import shell, shellcon
            return shell.SHGetFolderPath(0, shellcon.CSIDL_STARTUP, None, 0)
        except:
            # 备用方法
            return os.path.join(os.environ['APPDATA'], 
                              'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
    
    @staticmethod
    def open_startup_folder():
        """打开Windows启动文件夹"""
        try:
            import subprocess
            startup_folder = GlobalSettings.get_startup_folder()
            if os.path.exists(startup_folder):
                subprocess.Popen(f'explorer "{startup_folder}"')
                return True
            else:
                print(f"启动文件夹不存在: {startup_folder}")
                return False
        except Exception as e:
            print(f"打开启动文件夹失败: {e}")
            return False
    
    @staticmethod
    def get_program_path():
        """获取当前程序的路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的exe文件
            return sys.executable
        else:
            # Python脚本 - 使用路径管理器
            return path_manager.get_path('main.py')


class Settings:
    """角色配置管理类"""
    DEFAULT_SETTINGS = {
        'window_width': 240,
        'window_height': 135,
        'bg_width': 240,
        'bg_height': 135,
        'keyboard_x': 94,
        'keyboard_y': 84,
        'keyboard_width': 25,
        'keyboard_height': 25,
        'keyboard_press_offset': 5,
        'keyboard_horizontal_travel': 50,
        'mouse_x': 190,
        'mouse_y': 90,
        'mouse_width': 25,
        'mouse_height': 25,
        'max_mouse_offset': 20,
        'mouse_sensitivity': 0.3,
        'mouse_return_speed': 0.05,
        'sync_scale_enabled': False,
        'keypress_display_enabled': True,
        'keypress_display_x': 8,
        'keypress_display_y': 53,
        'keypress_display_font_size': 20
    }
    
    def __init__(self, character_name, character_folder):
        """初始化角色配置
        
        Args:
            character_name: 角色名称
            character_folder: 角色文件夹路径
        """
        self.character_name = character_name
        self.character_folder = character_folder
        self.config_file = os.path.join(character_folder, 'config.json')
        self.settings = self.load()
    
    def load(self):
        """加载角色配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    settings = self.DEFAULT_SETTINGS.copy()
                    settings.update(loaded)
                    
                    # 验证关键配置项，确保键盘动画能正常工作
                    if settings.get('keyboard_press_offset', 0) <= 0:
                        print(f"警告: {self.character_name}的keyboard_press_offset配置异常，使用默认值")
                        settings['keyboard_press_offset'] = self.DEFAULT_SETTINGS['keyboard_press_offset']
                    
                    return settings
            except Exception as e:
                print(f"加载{self.character_name}配置失败: {e}")
                return self.DEFAULT_SETTINGS.copy()
        return self.DEFAULT_SETTINGS.copy()
    
    def save(self):
        """保存角色配置（合并写入，保留 config.json 中其他字段如 layer_order）"""
        try:
            data = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            data.update(self.settings)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存{self.character_name}配置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取设置值"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """设置值"""
        self.settings[key] = value
    
    def reset(self):
        """重置为默认设置"""
        self.settings = self.DEFAULT_SETTINGS.copy()


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.parent_widget = parent
        
        # 获取全局设置
        self.global_settings = parent.global_settings if parent else None
        
        # 获取屏幕尺寸
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()
        
        # 暂停鼠标同步
        if self.parent_widget and hasattr(self.parent_widget, 'mouse_timer'):
            self.parent_widget.mouse_timer.stop()
        
        # 比例锁定标志
        self.bg_ratio_locked = True
        self.kb_ratio_locked = True
        self.mouse_ratio_locked = True
        
        # 保存初始比例
        self.bg_ratio = self.settings.get('bg_width') / max(self.settings.get('bg_height'), 1)
        self.kb_ratio = self.settings.get('keyboard_width') / max(self.settings.get('keyboard_height'), 1)
        self.mouse_ratio = self.settings.get('mouse_width') / max(self.settings.get('mouse_height'), 1)
        
        # 保存初始背景尺寸，用于计算缩放比例
        self.initial_bg_width = self.settings.get('bg_width')
        self.initial_bg_height = self.settings.get('bg_height')
        
        # 保存初始位置和尺寸，用于同步缩放
        self.initial_keyboard_x = self.settings.get('keyboard_x')
        self.initial_keyboard_y = self.settings.get('keyboard_y')
        self.initial_keyboard_width = self.settings.get('keyboard_width')
        self.initial_keyboard_height = self.settings.get('keyboard_height')
        self.initial_mouse_x = self.settings.get('mouse_x')
        self.initial_mouse_y = self.settings.get('mouse_y')
        self.initial_mouse_width = self.settings.get('mouse_width')
        self.initial_mouse_height = self.settings.get('mouse_height')
        
        # 鼠标同步测试标志
        self.mouse_sync_test = False
        
        self.init_ui()
        # connect_signals方法现在在create_image_adjustment_tab中调用
    
    def init_ui(self):
        self.setWindowTitle('设置')
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        
        # 保存保存按钮的引用，以便后续设置焦点
        self.save_btn = None
        
        # 创建选项卡控件
        self.tab_widget = QTabWidget()
        
        # 创建常规设置选项卡
        self.create_general_tab()
        
        # 创建图像调整选项卡
        self.create_image_adjustment_tab()
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton('重置默认')
        reset_btn.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.save_btn = QPushButton('保存')
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setDefault(True)
        button_layout.addWidget(self.save_btn)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab_widget)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
        
        # 默认显示常规设置选项卡
        self.tab_widget.setCurrentIndex(0)
        
        # 设置保存按钮焦点
        if self.save_btn:
            self.save_btn.setFocus()
    
    def create_general_tab(self):
        """创建常规设置选项卡"""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)
        
        # 开机自启设置
        startup_group = QGroupBox('启动设置')
        startup_layout = QVBoxLayout()
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 开机自启动教学按钮
        self.startup_guide_btn = QPushButton('开机自启动')
        self.startup_guide_btn.clicked.connect(self.show_startup_guide)
        button_layout.addWidget(self.startup_guide_btn)
        
        # 打开启动文件夹按钮
        self.open_startup_folder_btn = QPushButton('打开启动文件夹')
        self.open_startup_folder_btn.clicked.connect(self.open_startup_folder)
        button_layout.addWidget(self.open_startup_folder_btn)
        
        startup_layout.addLayout(button_layout)
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        layout.addStretch()
        
        self.tab_widget.addTab(general_widget, '常规设置')
    
    def create_image_adjustment_tab(self):
        """创建图像调整选项卡 - 现已移至图层管理器"""
        # 创建简单的提示页面
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # 添加提示信息
        info_label = QLabel('图像调整功能已移至图层管理器中。\n\n请通过右键菜单选择"自定义图层管理器"来调整图像位置、大小等属性。')
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet('QLabel { font-size: 14px; color: #666; padding: 50px; }')
        layout.addWidget(info_label)

        # 添加打开图层管理器的按钮
        open_button = QPushButton('打开图层管理器')
        open_button.clicked.connect(self.open_layer_manager)
        open_button.setMaximumWidth(200)
        layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

        self.tab_widget.addTab(content_widget, '图像调整')

    def open_layer_manager(self):
        """打开图层管理器"""
        if hasattr(self.parent(), 'open_custom_layer_manager'):
            self.parent().open_custom_layer_manager()
            self.close()  # 关闭设置对话框

        

    
    def connect_signals(self):
        """连接信号以实现实时预览 - 已移至图层管理器"""
        pass
    
    
    def show_startup_guide(self):
        """显示开机自启动教学"""
        from PyQt6.QtWidgets import QMessageBox
        
        program_path = GlobalSettings.get_program_path()
        startup_folder = GlobalSettings.get_startup_folder()
        
        guide_text = f"""<h3>开机自启动设置教程</h3>
<p><b>致歉</b></p>
<li>非常抱歉小伙伴！会者不难难者不会啊<br>
   我折磨了大半天写了好几次自动创建生成的快捷方式都没办法开机自启<br>
   只能出此下策麻烦小伙伴自己创建一个快捷方式放到启动文件夹了</li>
<p><b>手动创建快捷方式</b></p>
<ol>
<li>右键点击程序文件，选择"创建快捷方式"<br>
   应该显示的程序位置：<code>{program_path}</code></li>
<li>将创建的快捷方式移动到启动文件夹<br>
   启动文件夹的位置：<code>{startup_folder}</code></li>
   可以直接点击设置中的按钮打开
<li>重启电脑测试是否自动启动</li>
</ol>

<p><b>提示：</b>如果已经创建了快捷方式但无法自启动，请尝试：</p>
<ul>
<li>使用windows计划任务启动，详细操作可以询问ai</li>
</ul>"""
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("开机自启动教程")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(guide_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    
    def open_startup_folder(self):
        """打开Windows启动文件夹"""
        from PyQt6.QtWidgets import QMessageBox
        
        if GlobalSettings.open_startup_folder():
            QMessageBox.information(self, "成功", "已打开启动文件夹")
        else:
            startup_folder = GlobalSettings.get_startup_folder()
            QMessageBox.warning(self, "失败",
                              f"无法打开启动文件夹\n路径：{startup_folder}")

    def reset_settings(self):
        """重置为默认设置"""
        pass

    def save_settings(self):
        """保存设置"""
        # 只保存基本设置，图像调整设置在图层管理器中处理
        if self.settings.save():
            # 恢复鼠标同步
            if self.parent_widget and hasattr(self.parent_widget, 'mouse_timer'):
                self.parent_widget.mouse_timer.start(16)
            self.accept()
    
    def reject(self):
        """取消时恢复原始设置"""
        if self.parent_widget:
            # 恢复鼠标同步
            if hasattr(self.parent_widget, 'mouse_timer'):
                self.parent_widget.mouse_timer.start(16)
            # 重新加载原始设置并应用
            self.parent_widget.apply_settings()
        super().reject()
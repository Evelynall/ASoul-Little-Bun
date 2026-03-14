import json
import os
import sys
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QSpinBox, QPushButton, QGroupBox, QFormLayout,
                              QSlider, QScrollArea, QWidget, QApplication, QCheckBox, QTabWidget)
from PyQt6.QtCore import Qt


class GlobalSettings:
    """全局设置管理类"""
    DEFAULT_SETTINGS = {
        'window_x': 0,
        'window_y': 0,
        'last_character': None
    }
    
    def __init__(self, config_file='global_config.json'):
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
            # Python脚本
            return os.path.abspath(os.path.join(os.path.dirname(__file__), 'main.py'))


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
        'keyboard_horizontal_travel': 10,
        'mouse_x': 190,
        'mouse_y': 90,
        'mouse_width': 25,
        'mouse_height': 25,
        'max_mouse_offset': 20,
        'mouse_sensitivity': 0.3,
        'sync_scale_enabled': False
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
        """保存角色配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
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
        """创建图像调整选项卡"""
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建内容容器
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # 背景图片设置
        bg_group = QGroupBox('背景图片')
        bg_layout = QFormLayout()
        
        # 全体同步缩放开关
        self.sync_scale_checkbox = QCheckBox('全体同步缩放')
        self.sync_scale_checkbox.setChecked(self.settings.get('sync_scale_enabled', False))
        self.sync_scale_checkbox.setToolTip('开启后，背景缩放时其他图片会同步缩放和移动')
        self.sync_scale_checkbox.stateChanged.connect(self.on_sync_scale_changed)
        bg_layout.addRow('', self.sync_scale_checkbox)
        
        # 锁定比例开关
        self.bg_lock_ratio = QCheckBox('锁定比例')
        self.bg_lock_ratio.setChecked(True)
        self.bg_lock_ratio.stateChanged.connect(self.on_bg_lock_changed)
        bg_layout.addRow('', self.bg_lock_ratio)
        
        # 背景宽度
        bg_width_layout = QHBoxLayout()
        self.bg_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_width_slider.setRange(0, self.screen_width)
        self.bg_width_slider.setValue(self.settings.get('bg_width'))
        self.bg_width_spin = QSpinBox()
        self.bg_width_spin.setRange(0, self.screen_width)
        self.bg_width_spin.setValue(self.settings.get('bg_width'))
        self.bg_width_spin.setSuffix(' px')
        self.bg_width_slider.valueChanged.connect(self.on_bg_width_changed)
        self.bg_width_spin.valueChanged.connect(self.bg_width_slider.setValue)
        bg_width_layout.addWidget(self.bg_width_slider)
        bg_width_layout.addWidget(self.bg_width_spin)
        bg_layout.addRow('宽度:', bg_width_layout)
        
        # 背景高度
        bg_height_layout = QHBoxLayout()
        self.bg_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.bg_height_slider.setRange(0, self.screen_height)
        self.bg_height_slider.setValue(self.settings.get('bg_height'))
        self.bg_height_spin = QSpinBox()
        self.bg_height_spin.setRange(0, self.screen_height)
        self.bg_height_spin.setValue(self.settings.get('bg_height'))
        self.bg_height_spin.setSuffix(' px')
        self.bg_height_slider.valueChanged.connect(self.on_bg_height_changed)
        self.bg_height_spin.valueChanged.connect(self.bg_height_slider.setValue)
        bg_height_layout.addWidget(self.bg_height_slider)
        bg_height_layout.addWidget(self.bg_height_spin)
        bg_layout.addRow('高度:', bg_height_layout)
        
        bg_group.setLayout(bg_layout)
        layout.addWidget(bg_group)
        
        # 键盘图片设置
        keyboard_group = QGroupBox('键盘图片')
        keyboard_layout = QFormLayout()
        
        # 锁定比例开关
        self.kb_lock_ratio = QCheckBox('锁定比例')
        self.kb_lock_ratio.setChecked(True)
        self.kb_lock_ratio.stateChanged.connect(self.on_kb_lock_changed)
        keyboard_layout.addRow('', self.kb_lock_ratio)
        
        # 键盘 X 偏移
        kb_x_layout = QHBoxLayout()
        self.kb_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_x_slider.setRange(0, self.screen_width)
        self.kb_x_slider.setValue(self.settings.get('keyboard_x'))
        self.kb_x_spin = QSpinBox()
        self.kb_x_spin.setRange(0, self.screen_width)
        self.kb_x_spin.setValue(self.settings.get('keyboard_x'))
        self.kb_x_spin.setSuffix(' px')
        self.kb_x_slider.valueChanged.connect(self.kb_x_spin.setValue)
        self.kb_x_spin.valueChanged.connect(self.kb_x_slider.setValue)
        kb_x_layout.addWidget(self.kb_x_slider)
        kb_x_layout.addWidget(self.kb_x_spin)
        keyboard_layout.addRow('X 偏移:', kb_x_layout)
        
        # 键盘 Y 偏移
        kb_y_layout = QHBoxLayout()
        self.kb_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_y_slider.setRange(0, self.screen_height)
        self.kb_y_slider.setValue(self.settings.get('keyboard_y'))
        self.kb_y_spin = QSpinBox()
        self.kb_y_spin.setRange(0, self.screen_height)
        self.kb_y_spin.setValue(self.settings.get('keyboard_y'))
        self.kb_y_spin.setSuffix(' px')
        self.kb_y_slider.valueChanged.connect(self.kb_y_spin.setValue)
        self.kb_y_spin.valueChanged.connect(self.kb_y_slider.setValue)
        kb_y_layout.addWidget(self.kb_y_slider)
        kb_y_layout.addWidget(self.kb_y_spin)
        keyboard_layout.addRow('Y 偏移:', kb_y_layout)
        
        # 键盘按下偏移
        kb_press_layout = QHBoxLayout()
        self.kb_press_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_press_slider.setRange(0, self.screen_height)
        self.kb_press_slider.setValue(self.settings.get('keyboard_press_offset'))
        self.kb_press_spin = QSpinBox()
        self.kb_press_spin.setRange(0, self.screen_height)
        self.kb_press_spin.setValue(self.settings.get('keyboard_press_offset'))
        self.kb_press_spin.setSuffix(' px')
        self.kb_press_slider.valueChanged.connect(self.kb_press_spin.setValue)
        self.kb_press_spin.valueChanged.connect(self.kb_press_slider.setValue)
        kb_press_layout.addWidget(self.kb_press_slider)
        kb_press_layout.addWidget(self.kb_press_spin)
        keyboard_layout.addRow('按下偏移:', kb_press_layout)
        
        # 键盘水平移动范围
        kb_horizontal_layout = QHBoxLayout()
        self.kb_horizontal_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_horizontal_slider.setRange(0, 100)
        self.kb_horizontal_slider.setValue(self.settings.get('keyboard_horizontal_travel', 10))
        self.kb_horizontal_spin = QSpinBox()
        self.kb_horizontal_spin.setRange(0, 100)
        self.kb_horizontal_spin.setValue(self.settings.get('keyboard_horizontal_travel', 10))
        self.kb_horizontal_spin.setSuffix(' px')
        self.kb_horizontal_slider.valueChanged.connect(self.kb_horizontal_spin.setValue)
        self.kb_horizontal_spin.valueChanged.connect(self.kb_horizontal_slider.setValue)
        kb_horizontal_layout.addWidget(self.kb_horizontal_slider)
        kb_horizontal_layout.addWidget(self.kb_horizontal_spin)
        keyboard_layout.addRow('水平移动范围:', kb_horizontal_layout)
        
        # 键盘宽度
        kb_width_layout = QHBoxLayout()
        self.kb_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_width_slider.setRange(0, self.screen_width)
        self.kb_width_slider.setValue(self.settings.get('keyboard_width'))
        self.kb_width_spin = QSpinBox()
        self.kb_width_spin.setRange(0, self.screen_width)
        self.kb_width_spin.setValue(self.settings.get('keyboard_width'))
        self.kb_width_spin.setSuffix(' px')
        self.kb_width_slider.valueChanged.connect(self.on_kb_width_changed)
        self.kb_width_spin.valueChanged.connect(self.kb_width_slider.setValue)
        kb_width_layout.addWidget(self.kb_width_slider)
        kb_width_layout.addWidget(self.kb_width_spin)
        keyboard_layout.addRow('宽度:', kb_width_layout)
        
        # 键盘高度
        kb_height_layout = QHBoxLayout()
        self.kb_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.kb_height_slider.setRange(0, self.screen_height)
        self.kb_height_slider.setValue(self.settings.get('keyboard_height'))
        self.kb_height_spin = QSpinBox()
        self.kb_height_spin.setRange(0, self.screen_height)
        self.kb_height_spin.setValue(self.settings.get('keyboard_height'))
        self.kb_height_spin.setSuffix(' px')
        self.kb_height_slider.valueChanged.connect(self.on_kb_height_changed)
        self.kb_height_spin.valueChanged.connect(self.kb_height_slider.setValue)
        kb_height_layout.addWidget(self.kb_height_slider)
        kb_height_layout.addWidget(self.kb_height_spin)
        keyboard_layout.addRow('高度:', kb_height_layout)
        
        keyboard_group.setLayout(keyboard_layout)
        layout.addWidget(keyboard_group)
        
        # 鼠标图片设置
        mouse_group = QGroupBox('鼠标图片')
        mouse_layout = QFormLayout()
        
        # 锁定比例开关
        self.mouse_lock_ratio = QCheckBox('锁定比例')
        self.mouse_lock_ratio.setChecked(True)
        self.mouse_lock_ratio.stateChanged.connect(self.on_mouse_lock_changed)
        mouse_layout.addRow('', self.mouse_lock_ratio)
        
        # 鼠标 X 偏移
        mouse_x_layout = QHBoxLayout()
        self.mouse_x_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouse_x_slider.setRange(0, self.screen_width)
        self.mouse_x_slider.setValue(self.settings.get('mouse_x'))
        self.mouse_x_spin = QSpinBox()
        self.mouse_x_spin.setRange(0, self.screen_width)
        self.mouse_x_spin.setValue(self.settings.get('mouse_x'))
        self.mouse_x_spin.setSuffix(' px')
        self.mouse_x_slider.valueChanged.connect(self.mouse_x_spin.setValue)
        self.mouse_x_spin.valueChanged.connect(self.mouse_x_slider.setValue)
        mouse_x_layout.addWidget(self.mouse_x_slider)
        mouse_x_layout.addWidget(self.mouse_x_spin)
        mouse_layout.addRow('X 偏移:', mouse_x_layout)
        
        # 鼠标 Y 偏移
        mouse_y_layout = QHBoxLayout()
        self.mouse_y_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouse_y_slider.setRange(0, self.screen_height)
        self.mouse_y_slider.setValue(self.settings.get('mouse_y'))
        self.mouse_y_spin = QSpinBox()
        self.mouse_y_spin.setRange(0, self.screen_height)
        self.mouse_y_spin.setValue(self.settings.get('mouse_y'))
        self.mouse_y_spin.setSuffix(' px')
        self.mouse_y_slider.valueChanged.connect(self.mouse_y_spin.setValue)
        self.mouse_y_spin.valueChanged.connect(self.mouse_y_slider.setValue)
        mouse_y_layout.addWidget(self.mouse_y_slider)
        mouse_y_layout.addWidget(self.mouse_y_spin)
        mouse_layout.addRow('Y 偏移:', mouse_y_layout)
        
        # 最大移动范围和测试开关
        max_offset_layout = QHBoxLayout()
        self.max_offset_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_offset_slider.setRange(0, max(self.screen_width, self.screen_height))
        self.max_offset_slider.setValue(self.settings.get('max_mouse_offset'))
        self.max_offset_spin = QSpinBox()
        self.max_offset_spin.setRange(0, max(self.screen_width, self.screen_height))
        self.max_offset_spin.setValue(self.settings.get('max_mouse_offset'))
        self.max_offset_spin.setSuffix(' px')
        self.max_offset_slider.valueChanged.connect(self.max_offset_spin.setValue)
        self.max_offset_spin.valueChanged.connect(self.max_offset_slider.setValue)
        max_offset_layout.addWidget(self.max_offset_slider)
        max_offset_layout.addWidget(self.max_offset_spin)
        
        # 测试同步开关
        self.test_sync_checkbox = QCheckBox('测试同步')
        self.test_sync_checkbox.setChecked(False)
        self.test_sync_checkbox.stateChanged.connect(self.on_test_sync_changed)
        max_offset_layout.addWidget(self.test_sync_checkbox)
        
        mouse_layout.addRow('最大移动范围:', max_offset_layout)
        
        # 移动灵敏度
        sensitivity_layout = QHBoxLayout()
        self.sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self.sensitivity_slider.setRange(0, 1000)
        self.sensitivity_slider.setValue(int(self.settings.get('mouse_sensitivity') * 100))
        self.sensitivity_spin = QSpinBox()
        self.sensitivity_spin.setRange(0, 1000)
        self.sensitivity_spin.setValue(int(self.settings.get('mouse_sensitivity') * 100))
        self.sensitivity_spin.setSuffix(' %')
        self.sensitivity_slider.valueChanged.connect(self.sensitivity_spin.setValue)
        self.sensitivity_spin.valueChanged.connect(self.sensitivity_slider.setValue)
        sensitivity_layout.addWidget(self.sensitivity_slider)
        sensitivity_layout.addWidget(self.sensitivity_spin)
        mouse_layout.addRow('移动灵敏度:', sensitivity_layout)
        
        # 鼠标宽度
        mouse_width_layout = QHBoxLayout()
        self.mouse_width_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouse_width_slider.setRange(0, self.screen_width)
        self.mouse_width_slider.setValue(self.settings.get('mouse_width'))
        self.mouse_width_spin = QSpinBox()
        self.mouse_width_spin.setRange(0, self.screen_width)
        self.mouse_width_spin.setValue(self.settings.get('mouse_width'))
        self.mouse_width_spin.setSuffix(' px')
        self.mouse_width_slider.valueChanged.connect(self.on_mouse_width_changed)
        self.mouse_width_spin.valueChanged.connect(self.mouse_width_slider.setValue)
        mouse_width_layout.addWidget(self.mouse_width_slider)
        mouse_width_layout.addWidget(self.mouse_width_spin)
        mouse_layout.addRow('宽度:', mouse_width_layout)
        
        # 鼠标高度
        mouse_height_layout = QHBoxLayout()
        self.mouse_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.mouse_height_slider.setRange(0, self.screen_height)
        self.mouse_height_slider.setValue(self.settings.get('mouse_height'))
        self.mouse_height_spin = QSpinBox()
        self.mouse_height_spin.setRange(0, self.screen_height)
        self.mouse_height_spin.setValue(self.settings.get('mouse_height'))
        self.mouse_height_spin.setSuffix(' px')
        self.mouse_height_slider.valueChanged.connect(self.on_mouse_height_changed)
        self.mouse_height_spin.valueChanged.connect(self.mouse_height_slider.setValue)
        mouse_height_layout.addWidget(self.mouse_height_slider)
        mouse_height_layout.addWidget(self.mouse_height_spin)
        mouse_layout.addRow('高度:', mouse_height_layout)
        
        mouse_group.setLayout(mouse_layout)
        layout.addWidget(mouse_group)
        
        # 设置滚动区域
        scroll.setWidget(content_widget)
        
        self.tab_widget.addTab(scroll, '图像调整')
        
        # 连接信号以实现实时预览
        self.connect_signals()
        

    
    def connect_signals(self):
        """连接信号以实现实时预览"""
        # 背景图片
        self.bg_width_spin.valueChanged.connect(self.apply_preview)
        self.bg_height_spin.valueChanged.connect(self.apply_preview)
        
        # 键盘图片
        self.kb_x_spin.valueChanged.connect(self.apply_preview)
        self.kb_y_spin.valueChanged.connect(self.apply_preview)
        self.kb_width_spin.valueChanged.connect(self.apply_preview)
        self.kb_height_spin.valueChanged.connect(self.apply_preview)
        self.kb_press_spin.valueChanged.connect(self.apply_preview)
        self.kb_horizontal_spin.valueChanged.connect(self.apply_preview)
        
        # 鼠标图片
        self.mouse_x_spin.valueChanged.connect(self.apply_preview)
        self.mouse_y_spin.valueChanged.connect(self.apply_preview)
        self.mouse_width_spin.valueChanged.connect(self.apply_preview)
        self.mouse_height_spin.valueChanged.connect(self.apply_preview)
        self.max_offset_spin.valueChanged.connect(self.apply_preview)
        self.sensitivity_spin.valueChanged.connect(self.apply_preview)
    
    
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

    def on_sync_scale_changed(self, state):
        """全体同步缩放状态改变"""
        sync_enabled = (state == Qt.CheckState.Checked.value)
        if sync_enabled:
            # 重新记录当前作为基准的初始值
            self.initial_bg_width = self.bg_width_spin.value()
            self.initial_bg_height = self.bg_height_spin.value()
            self.initial_keyboard_x = self.kb_x_spin.value()
            self.initial_keyboard_y = self.kb_y_spin.value()
            self.initial_keyboard_width = self.kb_width_spin.value()
            self.initial_keyboard_height = self.kb_height_spin.value()
            self.initial_mouse_x = self.mouse_x_spin.value()
            self.initial_mouse_y = self.mouse_y_spin.value()
            self.initial_mouse_width = self.mouse_width_spin.value()
            self.initial_mouse_height = self.mouse_height_spin.value()
    
    def on_bg_lock_changed(self, state):
        """背景比例锁定状态改变"""
        self.bg_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.bg_ratio_locked:
            self.bg_ratio = self.bg_width_spin.value() / max(self.bg_height_spin.value(), 1)
    
    def on_kb_lock_changed(self, state):
        """键盘比例锁定状态改变"""
        self.kb_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.kb_ratio_locked:
            self.kb_ratio = self.kb_width_spin.value() / max(self.kb_height_spin.value(), 1)
    
    def on_mouse_lock_changed(self, state):
        """鼠标比例锁定状态改变"""
        self.mouse_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.mouse_ratio_locked:
            self.mouse_ratio = self.mouse_width_spin.value() / max(self.mouse_height_spin.value(), 1)
    
    def on_bg_width_changed(self, value):
        """背景宽度改变"""
        self.bg_width_spin.setValue(value)
        if self.bg_ratio_locked and value > 0:
            new_height = int(value / self.bg_ratio)
            self.bg_height_slider.blockSignals(True)
            self.bg_height_spin.blockSignals(True)
            self.bg_height_slider.setValue(new_height)
            self.bg_height_spin.setValue(new_height)
            self.bg_height_slider.blockSignals(False)
            self.bg_height_spin.blockSignals(False)
        
        # 全体同步缩放
        if self.sync_scale_checkbox.isChecked() and self.initial_bg_width > 0:
            self.sync_all_elements()
    
    def on_bg_height_changed(self, value):
        """背景高度改变"""
        self.bg_height_spin.setValue(value)
        if self.bg_ratio_locked and value > 0:
            new_width = int(value * self.bg_ratio)
            self.bg_width_slider.blockSignals(True)
            self.bg_width_spin.blockSignals(True)
            self.bg_width_slider.setValue(new_width)
            self.bg_width_spin.setValue(new_width)
            self.bg_width_slider.blockSignals(False)
            self.bg_width_spin.blockSignals(False)
        
        # 全体同步缩放
        if self.sync_scale_checkbox.isChecked() and self.initial_bg_height > 0:
            self.sync_all_elements()
    
    def sync_all_elements(self):
        """同步缩放所有元素"""
        if self.initial_bg_width <= 0 or self.initial_bg_height <= 0:
            return
        
        # 计算缩放比例
        scale_x = self.bg_width_spin.value() / self.initial_bg_width
        scale_y = self.bg_height_spin.value() / self.initial_bg_height
        
        # 阻止信号以避免递归调用
        self.kb_x_slider.blockSignals(True)
        self.kb_x_spin.blockSignals(True)
        self.kb_y_slider.blockSignals(True)
        self.kb_y_spin.blockSignals(True)
        self.kb_width_slider.blockSignals(True)
        self.kb_width_spin.blockSignals(True)
        self.kb_height_slider.blockSignals(True)
        self.kb_height_spin.blockSignals(True)
        
        self.mouse_x_slider.blockSignals(True)
        self.mouse_x_spin.blockSignals(True)
        self.mouse_y_slider.blockSignals(True)
        self.mouse_y_spin.blockSignals(True)
        self.mouse_width_slider.blockSignals(True)
        self.mouse_width_spin.blockSignals(True)
        self.mouse_height_slider.blockSignals(True)
        self.mouse_height_spin.blockSignals(True)
        
        # 同步键盘位置和尺寸
        new_kb_x = int(self.initial_keyboard_x * scale_x)
        new_kb_y = int(self.initial_keyboard_y * scale_y)
        new_kb_width = int(self.initial_keyboard_width * scale_x)
        new_kb_height = int(self.initial_keyboard_height * scale_y)
        
        self.kb_x_slider.setValue(new_kb_x)
        self.kb_x_spin.setValue(new_kb_x)
        self.kb_y_slider.setValue(new_kb_y)
        self.kb_y_spin.setValue(new_kb_y)
        self.kb_width_slider.setValue(new_kb_width)
        self.kb_width_spin.setValue(new_kb_width)
        self.kb_height_slider.setValue(new_kb_height)
        self.kb_height_spin.setValue(new_kb_height)
        
        # 同步鼠标位置和尺寸
        new_mouse_x = int(self.initial_mouse_x * scale_x)
        new_mouse_y = int(self.initial_mouse_y * scale_y)
        new_mouse_width = int(self.initial_mouse_width * scale_x)
        new_mouse_height = int(self.initial_mouse_height * scale_y)
        
        self.mouse_x_slider.setValue(new_mouse_x)
        self.mouse_x_spin.setValue(new_mouse_x)
        self.mouse_y_slider.setValue(new_mouse_y)
        self.mouse_y_spin.setValue(new_mouse_y)
        self.mouse_width_slider.setValue(new_mouse_width)
        self.mouse_width_spin.setValue(new_mouse_width)
        self.mouse_height_slider.setValue(new_mouse_height)
        self.mouse_height_spin.setValue(new_mouse_height)
        
        # 恢复信号
        self.kb_x_slider.blockSignals(False)
        self.kb_x_spin.blockSignals(False)
        self.kb_y_slider.blockSignals(False)
        self.kb_y_spin.blockSignals(False)
        self.kb_width_slider.blockSignals(False)
        self.kb_width_spin.blockSignals(False)
        self.kb_height_slider.blockSignals(False)
        self.kb_height_spin.blockSignals(False)
        
        self.mouse_x_slider.blockSignals(False)
        self.mouse_x_spin.blockSignals(False)
        self.mouse_y_slider.blockSignals(False)
        self.mouse_y_spin.blockSignals(False)
        self.mouse_width_slider.blockSignals(False)
        self.mouse_width_spin.blockSignals(False)
        self.mouse_height_slider.blockSignals(False)
        self.mouse_height_spin.blockSignals(False)
    
    def on_kb_width_changed(self, value):
        """键盘宽度改变"""
        self.kb_width_spin.setValue(value)
        if self.kb_ratio_locked and value > 0:
            new_height = int(value / self.kb_ratio)
            self.kb_height_slider.blockSignals(True)
            self.kb_height_spin.blockSignals(True)
            self.kb_height_slider.setValue(new_height)
            self.kb_height_spin.setValue(new_height)
            self.kb_height_slider.blockSignals(False)
            self.kb_height_spin.blockSignals(False)
    
    def on_kb_height_changed(self, value):
        """键盘高度改变"""
        self.kb_height_spin.setValue(value)
        if self.kb_ratio_locked and value > 0:
            new_width = int(value * self.kb_ratio)
            self.kb_width_slider.blockSignals(True)
            self.kb_width_spin.blockSignals(True)
            self.kb_width_slider.setValue(new_width)
            self.kb_width_spin.setValue(new_width)
            self.kb_width_slider.blockSignals(False)
            self.kb_width_spin.blockSignals(False)
    
    def on_mouse_width_changed(self, value):
        """鼠标宽度改变"""
        self.mouse_width_spin.setValue(value)
        if self.mouse_ratio_locked and value > 0:
            new_height = int(value / self.mouse_ratio)
            self.mouse_height_slider.blockSignals(True)
            self.mouse_height_spin.blockSignals(True)
            self.mouse_height_slider.setValue(new_height)
            self.mouse_height_spin.setValue(new_height)
            self.mouse_height_slider.blockSignals(False)
            self.mouse_height_spin.blockSignals(False)
    
    def on_mouse_height_changed(self, value):
        """鼠标高度改变"""
        self.mouse_height_spin.setValue(value)
        if self.mouse_ratio_locked and value > 0:
            new_width = int(value * self.mouse_ratio)
            self.mouse_width_slider.blockSignals(True)
            self.mouse_width_spin.blockSignals(True)
            self.mouse_width_slider.setValue(new_width)
            self.mouse_width_spin.setValue(new_width)
            self.mouse_width_slider.blockSignals(False)
            self.mouse_width_spin.blockSignals(False)
    
    def on_test_sync_changed(self, state):
        """测试同步开关改变"""
        self.mouse_sync_test = (state == Qt.CheckState.Checked.value)
        if self.parent_widget and hasattr(self.parent_widget, 'mouse_timer'):
            if self.mouse_sync_test:
                # 启动鼠标同步测试
                self.parent_widget.mouse_timer.start(16)
            else:
                # 停止鼠标同步测试
                self.parent_widget.mouse_timer.stop()
    
    def apply_preview(self):
        """实时应用预览效果"""
        if not self.parent_widget:
            return
        
        # 获取最大的图片尺寸作为窗口大小
        max_width = max(self.bg_width_spin.value(), 
                       self.kb_width_spin.value() + self.kb_x_spin.value(),
                       self.mouse_width_spin.value() + self.mouse_x_spin.value())
        max_height = max(self.bg_height_spin.value(),
                        self.kb_height_spin.value() + self.kb_y_spin.value(),
                        self.mouse_height_spin.value() + self.mouse_y_spin.value())
        
        # 临时更新父窗口的设置（不保存到文件）
        temp_settings = {
            'window_width': max_width,
            'window_height': max_height,
            'bg_width': self.bg_width_spin.value(),
            'bg_height': self.bg_height_spin.value(),
            'keyboard_x': self.kb_x_spin.value(),
            'keyboard_y': self.kb_y_spin.value(),
            'keyboard_width': self.kb_width_spin.value(),
            'keyboard_height': self.kb_height_spin.value(),
            'keyboard_press_offset': self.kb_press_spin.value(),
            'keyboard_horizontal_travel': self.kb_horizontal_spin.value(),
            'mouse_x': self.mouse_x_spin.value(),
            'mouse_y': self.mouse_y_spin.value(),
            'mouse_width': self.mouse_width_spin.value(),
            'mouse_height': self.mouse_height_spin.value(),
            'max_mouse_offset': self.max_offset_spin.value(),
            'mouse_sensitivity': self.sensitivity_spin.value() / 100.0
        }
        
        # 临时保存原始设置
        original_settings = {}
        for key in temp_settings:
            original_settings[key] = self.settings.get(key)
            self.settings.set(key, temp_settings[key])
        
        # 应用预览
        self.parent_widget.apply_settings()
        
        # 恢复原始设置（不保存到文件）
        for key, value in original_settings.items():
            self.settings.set(key, value)
    
    def reset_settings(self):
        """重置为默认设置"""
        self.bg_width_spin.setValue(Settings.DEFAULT_SETTINGS['bg_width'])
        self.bg_height_spin.setValue(Settings.DEFAULT_SETTINGS['bg_height'])
        self.kb_x_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_x'])
        self.kb_y_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_y'])
        self.kb_width_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_width'])
        self.kb_height_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_height'])
        self.kb_press_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_press_offset'])
        self.kb_horizontal_spin.setValue(Settings.DEFAULT_SETTINGS['keyboard_horizontal_travel'])
        self.mouse_x_spin.setValue(Settings.DEFAULT_SETTINGS['mouse_x'])
        self.mouse_y_spin.setValue(Settings.DEFAULT_SETTINGS['mouse_y'])
        self.mouse_width_spin.setValue(Settings.DEFAULT_SETTINGS['mouse_width'])
        self.mouse_height_spin.setValue(Settings.DEFAULT_SETTINGS['mouse_height'])
        self.max_offset_spin.setValue(Settings.DEFAULT_SETTINGS['max_mouse_offset'])
        self.sensitivity_spin.setValue(int(Settings.DEFAULT_SETTINGS['mouse_sensitivity'] * 100))
        self.sync_scale_checkbox.setChecked(Settings.DEFAULT_SETTINGS['sync_scale_enabled'])
        # 重置后立即应用预览
        self.apply_preview()
    
    def save_settings(self):
        """保存设置"""
        # 计算窗口大小
        max_width = max(self.bg_width_spin.value(), 
                       self.kb_width_spin.value() + self.kb_x_spin.value(),
                       self.mouse_width_spin.value() + self.mouse_x_spin.value())
        max_height = max(self.bg_height_spin.value(),
                        self.kb_height_spin.value() + self.kb_y_spin.value(),
                        self.mouse_height_spin.value() + self.mouse_y_spin.value())
        
        self.settings.set('window_width', max_width)
        self.settings.set('window_height', max_height)
        self.settings.set('bg_width', self.bg_width_spin.value())
        self.settings.set('bg_height', self.bg_height_spin.value())
        self.settings.set('keyboard_x', self.kb_x_spin.value())
        self.settings.set('keyboard_y', self.kb_y_spin.value())
        self.settings.set('keyboard_width', self.kb_width_spin.value())
        self.settings.set('keyboard_height', self.kb_height_spin.value())
        self.settings.set('keyboard_press_offset', self.kb_press_spin.value())
        self.settings.set('keyboard_horizontal_travel', self.kb_horizontal_spin.value())
        self.settings.set('mouse_x', self.mouse_x_spin.value())
        self.settings.set('mouse_y', self.mouse_y_spin.value())
        self.settings.set('mouse_width', self.mouse_width_spin.value())
        self.settings.set('mouse_height', self.mouse_height_spin.value())
        self.settings.set('max_mouse_offset', self.max_offset_spin.value())
        self.settings.set('mouse_sensitivity', self.sensitivity_spin.value() / 100.0)
        self.settings.set('sync_scale_enabled', self.sync_scale_checkbox.isChecked())
        
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
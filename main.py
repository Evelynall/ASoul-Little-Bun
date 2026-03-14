import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu, QDialog, QSystemTrayIcon, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QPainter, QCursor, QAction, QIcon, QSurfaceFormat
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from pynput import keyboard, mouse
from settings import Settings, GlobalSettings, SettingsDialog
from update_checker import UpdateChecker


class ASoulLittleBun(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        # 加载全局设置
        self.global_settings = GlobalSettings()
        
        # 窗口状态设置（默认置顶、不穿透、隐藏任务栏、不锁定鼠标）
        self.always_on_top = self.global_settings.get('always_on_top', True)
        self.mouse_passthrough = self.global_settings.get('mouse_passthrough', False)
        self.hide_taskbar = self.global_settings.get('hide_taskbar', True)
        self.mouse_locked = self.global_settings.get('mouse_locked', False)
        
        self.characters = self.load_characters()
        
        # 加载上次使用的角色
        last_character = self.global_settings.get('last_character')
        if last_character and last_character in self.characters:
            self.current_character = last_character
            character_list = list(self.characters.keys())
            self.current_character_index = character_list.index(last_character)
        else:
            # 如果没有保存的角色或角色不存在，使用第一个角色
            if self.characters:
                self.current_character_index = 0
                self.current_character = list(self.characters.keys())[0]
            else:
                # 如果没有任何角色，设置为None
                self.current_character_index = 0
                self.current_character = None
        
        # 加载当前角色的配置
        self.load_character_settings()
        
        # 从设置中读取窗口大小
        self.window_width = self.settings.get('window_width')
        self.window_height = self.settings.get('window_height')
        
        # 初始化系统托盘
        self.init_tray()
        
        self.init_ui()
        
        # 鼠标同步移动相关
        self.last_mouse_pos = QCursor.pos()
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.max_mouse_offset = self.settings.get('max_mouse_offset')
        self.mouse_sensitivity = self.settings.get('mouse_sensitivity')
        
        # 鼠标位置突变过滤相关
        self.mouse_jump_threshold = 100  # 超过此距离视为突变（像素）
        self.mouse_velocity_x = 0  # 鼠标速度（用于平滑）
        self.mouse_velocity_y = 0
        self.velocity_smoothing = 0.3  # 速度平滑系数（0-1，越小越平滑）
        
        # 键盘动画相关
        self.keyboard_offset_y = 0
        self.keyboard_animation = None
        
        # 启动监听器
        self.start_listeners()
        
        # 启动鼠标同步定时器
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self.update_mouse_position)
        self.mouse_timer.start(16)  # 约60fps
    
    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.always_on_top = not self.always_on_top
        self.global_settings.set('always_on_top', self.always_on_top)
        self.global_settings.save()
        
        # 重新设置窗口标志
        flags = Qt.WindowType.FramelessWindowHint
        
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.show()  # 重新显示窗口以应用新的标志
        
        # 更新托盘菜单以同步勾选状态
        self.create_tray_menu()
    
    def toggle_mouse_passthrough(self):
        """切换鼠标穿透状态"""
        self.mouse_passthrough = not self.mouse_passthrough
        self.global_settings.set('mouse_passthrough', self.mouse_passthrough)
        self.global_settings.save()
        
        # 应用鼠标穿透设置
        self.apply_mouse_passthrough()
        
        # 更新托盘菜单以同步勾选状态
        self.create_tray_menu()
    
    def toggle_hide_taskbar(self):
        """切换隐藏任务栏状态"""
        from PyQt6.QtWidgets import QMessageBox
        
        # 如果要开启隐藏任务栏，先显示警告
        if not self.hide_taskbar:
            reply = QMessageBox.question(
                self, 
                '隐藏任务栏确认',
                '启用隐藏任务栏功能后，OBS将无法识别此窗口。\n\n是否继续？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.hide_taskbar = not self.hide_taskbar
        self.global_settings.set('hide_taskbar', self.hide_taskbar)
        self.global_settings.save()
        
        # 应用隐藏任务栏设置
        self.apply_hide_taskbar()
        
        # 更新托盘菜单以同步勾选状态
        self.create_tray_menu()
    
    def toggle_mouse_locked(self):
        """切换鼠标锁定状态"""
        self.mouse_locked = not self.mouse_locked
        self.global_settings.set('mouse_locked', self.mouse_locked)
        self.global_settings.save()
        
        # 如果锁定鼠标，重置鼠标偏移和速度到中心位置
        if self.mouse_locked:
            self.mouse_offset_x = 0
            self.mouse_offset_y = 0
            self.mouse_velocity_x = 0
            self.mouse_velocity_y = 0
            base_x = self.settings.get('mouse_x')
            base_y = self.settings.get('mouse_y')
            mouse_width = self.settings.get('mouse_width')
            mouse_height = self.settings.get('mouse_height')
            self.mouse_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
            self.left_click_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
            self.right_click_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
        else:
            # 解锁时也重置速度，避免突然的移动
            self.mouse_velocity_x = 0
            self.mouse_velocity_y = 0
        
        # 更新托盘菜单以同步勾选状态
        self.create_tray_menu()
    
    def apply_mouse_passthrough(self):
        """应用鼠标穿透设置到窗口和所有子控件"""
        if self.mouse_passthrough:
            # 设置主窗口鼠标穿透
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            # 设置所有子控件鼠标穿透
            for child in self.findChildren(QLabel):
                child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            
            # 额外设置：使用窗口标志来确保鼠标穿透
            current_flags = self.windowFlags()
            self.setWindowFlags(current_flags | Qt.WindowType.WindowTransparentForInput)
            self.show()  # 重新显示以应用标志
        else:
            # 取消主窗口鼠标穿透
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            # 取消所有子控件鼠标穿透
            for child in self.findChildren(QLabel):
                child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            
            # 移除窗口标志
            current_flags = self.windowFlags()
            self.setWindowFlags(current_flags & ~Qt.WindowType.WindowTransparentForInput)
            self.show()  # 重新显示以应用标志
    
    def load_character_settings(self):
        """加载当前角色的配置"""
        if not self.current_character:
            # 如果没有角色，创建一个默认的Settings实例
            self.settings = Settings('default', 'img')
            return
        
        character_folder = os.path.join('img', self.current_character)
        self.settings = Settings(self.current_character, character_folder)
        
        # 验证并修复配置
        config_changed = False
        
        # 检查keyboard_press_offset
        if self.settings.get('keyboard_press_offset', 0) <= 0:
            print(f"修复配置: {self.current_character}的keyboard_press_offset设置为默认值5")
            self.settings.set('keyboard_press_offset', 5)
            config_changed = True
        
        # 检查其他关键配置
        critical_keys = ['keyboard_x', 'keyboard_y', 'keyboard_width', 'keyboard_height']
        for key in critical_keys:
            if self.settings.get(key) is None:
                print(f"修复配置: {self.current_character}的{key}缺失，使用默认值")
                self.settings.set(key, Settings.DEFAULT_SETTINGS[key])
                config_changed = True
        
        # 如果配置被修改，保存到文件
        if config_changed:
            self.settings.save()
            print(f"已自动修复{self.current_character}的配置文件")
    
    def init_tray(self):
        """初始化系统托盘"""
        # 检查系统是否支持托盘
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "系统托盘", "系统不支持托盘功能")
            return
        
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置托盘图标 - 使用当前角色的背景图片作为托盘图标
        self.update_tray_icon()
        
        # 创建托盘菜单
        self.create_tray_menu()
        
        # 连接托盘图标的激活信号
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 显示托盘消息
        self.tray_icon.showMessage(
            "桌面宠物",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def update_tray_icon(self):
        """更新托盘图标"""
        if hasattr(self, 'tray_icon'):
            # 使用统一的托盘图标
            icon_path = 'img/icon.png'
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                # 缩放到合适的托盘图标大小
                scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon = QIcon(scaled_pixmap)
                self.tray_icon.setIcon(icon)
            else:
                # 如果没有图片，使用默认图标
                self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
    
    def create_tray_menu(self):
        """创建托盘菜单"""
        tray_menu = QMenu()
        
        # 显示/隐藏窗口
        show_action = QAction("显示/隐藏", self)
        show_action.triggered.connect(self.toggle_window_visibility)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 窗口设置二级菜单
        window_settings_menu = tray_menu.addMenu('窗口设置')
        
        # 置顶开关
        always_on_top_action = QAction('窗口置顶', self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        window_settings_menu.addAction(always_on_top_action)
        
        # 鼠标穿透开关
        mouse_passthrough_action = QAction('鼠标穿透', self)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.toggle_mouse_passthrough)
        window_settings_menu.addAction(mouse_passthrough_action)
        
        # 隐藏任务栏开关
        hide_taskbar_action = QAction('隐藏任务栏 (OBS不可识别)', self)
        hide_taskbar_action.setCheckable(True)
        hide_taskbar_action.setChecked(self.hide_taskbar)
        hide_taskbar_action.triggered.connect(self.toggle_hide_taskbar)
        window_settings_menu.addAction(hide_taskbar_action)
        
        tray_menu.addSeparator()
        
        # 锁定鼠标开关
        mouse_locked_action = QAction('锁定鼠标', self)
        mouse_locked_action.setCheckable(True)
        mouse_locked_action.setChecked(self.mouse_locked)
        mouse_locked_action.triggered.connect(self.toggle_mouse_locked)
        tray_menu.addAction(mouse_locked_action)
        
        tray_menu.addSeparator()
        
        # 切换角色菜单
        if self.characters:
            character_menu = tray_menu.addMenu('切换角色')
            for character in self.characters.keys():
                char_action = QAction(character, self)
                char_action.triggered.connect(lambda checked, c=character: self.switch_to_character(c))
                character_menu.addAction(char_action)
            
            tray_menu.addSeparator()
        
        # 设置菜单
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)
        
        # 关于菜单
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        tray_menu.addAction(about_action)
        
        tray_menu.addSeparator()
        
        # 退出菜单
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
    
    def tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window_visibility()
    
    def toggle_window_visibility(self):
        """切换窗口显示/隐藏状态"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def quit_application(self):
        """退出应用程序"""
        self.close()
    
    def init_ui(self):
        # 设置基础窗口属性 - 保持OBS兼容性
        flags = Qt.WindowType.FramelessWindowHint
        
        # 根据设置决定是否置顶
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, self.always_on_top)
        
        # 设置窗口标题以便OBS识别
        self.setWindowTitle("ASoul Little Bun")
        
        # 确保窗口在任务栏中可见（对OBS识别有帮助）
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        
        # 设置窗口图标（有助于OBS识别）
        if hasattr(self, 'characters') and self.current_character:
            icon_path = f"img/{self.current_character}/bgImage.png"
            try:
                from PyQt6.QtGui import QIcon
                self.setWindowIcon(QIcon(icon_path))
            except:
                pass
        
        # 设置窗口大小
        self.resize(self.window_width, self.window_height)
        
        # 设置窗口位置到屏幕中心或读取保存的位置
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        window_x = self.global_settings.get('window_x')
        window_y = self.global_settings.get('window_y')
        
        # 如果没有保存的位置，则设置到屏幕中心
        if window_x is None or window_y is None:
            center_x = (screen_geometry.width() - self.window_width) // 2
            center_y = (screen_geometry.height() - self.window_height) // 2
            self.move(center_x, center_y)
        else:
            self.move(window_x, window_y)
        
        # 创建图层标签
        self.bg_label = QLabel(self)
        self.keyboard_label = QLabel(self)
        self.mouse_label = QLabel(self)
        self.left_click_label = QLabel(self)
        self.right_click_label = QLabel(self)
        
        # 加载当前角色图片
        self.load_character_images()
        
        # 应用鼠标穿透设置（在创建子控件后）
        self.apply_mouse_passthrough()
        
        # 允许拖动窗口
        self.dragging = False
        self.drag_position = QPoint()
        
        self.show()
        
        # 根据设置决定是否隐藏任务栏
        if self.hide_taskbar:
            self.hide_from_taskbar()
        
        # 显示首次启动提示（只显示一次）
        self.show_first_launch_tip()
        
        # 检查更新（在窗口显示后）
        QTimer.singleShot(1000, self.check_for_updates)
    
    def paintEvent(self, event):
        """重写 paintEvent 以支持 OpenGL 渲染和透明背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        # 填充透明背景
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
    
    def load_characters(self):
        """自动识别img目录下的角色文件夹"""
        characters = {}
        img_dir = 'img'
        
        if not os.path.exists(img_dir):
            return characters
        
        for folder in os.listdir(img_dir):
            folder_path = os.path.join(img_dir, folder)
            if os.path.isdir(folder_path):
                bg_path = os.path.join(folder_path, 'bgImage.png')
                keyboard_path = os.path.join(folder_path, 'keyboardImage.png')
                mouse_path = os.path.join(folder_path, 'mouseImage.png')
                left_click_path = os.path.join(folder_path, 'leftClickImage.png')
                right_click_path = os.path.join(folder_path, 'rightClickImage.png')
                
                if all(os.path.exists(p) for p in [bg_path, keyboard_path, mouse_path]):
                    characters[folder] = {
                        'bg': bg_path,
                        'keyboard': keyboard_path,
                        'mouse': mouse_path,
                        'left_click': left_click_path if os.path.exists(left_click_path) else None,
                        'right_click': right_click_path if os.path.exists(right_click_path) else None
                    }
        
        return characters
    
    def load_character_images(self):
        """加载当前角色的图片"""
        if not self.current_character or self.current_character not in self.characters:
            return
        
        char_data = self.characters[self.current_character]
        
        # 加载背景图片，使用独立的大小设置
        bg_pixmap = QPixmap(char_data['bg'])
        self.bg_label.setPixmap(bg_pixmap)
        bg_width = self.settings.get('bg_width')
        bg_height = self.settings.get('bg_height')
        self.bg_label.setGeometry(0, 0, bg_width, bg_height)
        self.bg_label.setScaledContents(True)
        
        # 加载键盘图片，应用设置中的偏移和大小
        keyboard_pixmap = QPixmap(char_data['keyboard'])
        self.keyboard_label.setPixmap(keyboard_pixmap)
        kb_x = self.settings.get('keyboard_x')
        kb_y = self.settings.get('keyboard_y')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        self.keyboard_label.setGeometry(kb_x, kb_y, kb_width, kb_height)
        self.keyboard_label.setScaledContents(True)
        
        # 加载鼠标图片，应用设置中的偏移和大小
        mouse_pixmap = QPixmap(char_data['mouse'])
        self.mouse_label.setPixmap(mouse_pixmap)
        mouse_x = self.settings.get('mouse_x')
        mouse_y = self.settings.get('mouse_y')
        mouse_width = self.settings.get('mouse_width')
        mouse_height = self.settings.get('mouse_height')
        self.mouse_label.setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
        self.mouse_label.setScaledContents(True)
        
        # 加载左键图片（初始隐藏）
        if char_data['left_click'] and os.path.exists(char_data['left_click']):
            left_click_pixmap = QPixmap(char_data['left_click'])
            self.left_click_label.setPixmap(left_click_pixmap)
            self.left_click_label.setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
            self.left_click_label.setScaledContents(True)
        self.left_click_label.hide()
        
        # 加载右键图片（初始隐藏）
        if char_data['right_click'] and os.path.exists(char_data['right_click']):
            right_click_pixmap = QPixmap(char_data['right_click'])
            self.right_click_label.setPixmap(right_click_pixmap)
            self.right_click_label.setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
            self.right_click_label.setScaledContents(True)
        self.right_click_label.hide()
    
    def switch_to_character(self, character_name):
        """切换到指定角色"""
        if character_name not in self.characters:
            return
        
        self.current_character = character_name
        character_list = list(self.characters.keys())
        self.current_character_index = character_list.index(character_name)
        
        # 保存当前角色到全局配置
        self.global_settings.set('last_character', character_name)
        self.global_settings.save()
        
        # 加载新角色的配置
        self.load_character_settings()
        
        # 应用新配置
        self.apply_settings()
    
    def start_listeners(self):
        """启动键盘和鼠标监听器"""
        # 键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release
        )
        self.keyboard_listener.daemon = True  # 设置为守护线程
        self.keyboard_listener.start()
        
        # 鼠标监听
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click
        )
        self.mouse_listener.daemon = True  # 设置为守护线程
        self.mouse_listener.start()
    
    def on_key_press(self, key):
        """键盘按下事件"""
        # 使用QTimer在主线程中执行UI更新
        QTimer.singleShot(0, self.animate_key_press)
    
    def on_key_release(self, key):
        """键盘释放事件"""
        # 使用QTimer在主线程中执行UI更新
        QTimer.singleShot(0, self.animate_key_release)
    
    def on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        if pressed:
            # 鼠标按下
            if button == mouse.Button.left:
                QTimer.singleShot(0, self.show_left_click)
            elif button == mouse.Button.right:
                QTimer.singleShot(0, self.show_right_click)
        else:
            # 鼠标释放
            QTimer.singleShot(0, self.hide_click_images)
    
    def animate_key_press(self):
        """键盘按下动画"""
        if self.keyboard_animation and self.keyboard_animation.state() == QPropertyAnimation.State.Running:
            self.keyboard_animation.stop()
        
        kb_x = self.settings.get('keyboard_x')
        kb_y = self.settings.get('keyboard_y')
        press_offset = self.settings.get('keyboard_press_offset')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        
        # 调试信息：检查配置是否正确加载
        if press_offset is None or press_offset <= 0:
            print(f"警告: 键盘按下偏移量异常 (press_offset={press_offset})，角色: {self.current_character}")
            press_offset = 5  # 使用默认值
        
        self.keyboard_animation = QPropertyAnimation(self.keyboard_label, b"geometry")
        self.keyboard_animation.setDuration(50)
        self.keyboard_animation.setStartValue(self.keyboard_label.geometry())
        self.keyboard_animation.setEndValue(QRect(kb_x, kb_y + press_offset, kb_width, kb_height))
        self.keyboard_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.keyboard_animation.start()
    
    def animate_key_release(self):
        """键盘释放动画"""
        if self.keyboard_animation and self.keyboard_animation.state() == QPropertyAnimation.State.Running:
            self.keyboard_animation.stop()
        
        kb_x = self.settings.get('keyboard_x')
        kb_y = self.settings.get('keyboard_y')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        
        self.keyboard_animation = QPropertyAnimation(self.keyboard_label, b"geometry")
        self.keyboard_animation.setDuration(100)
        self.keyboard_animation.setStartValue(self.keyboard_label.geometry())
        self.keyboard_animation.setEndValue(QRect(kb_x, kb_y, kb_width, kb_height))
        self.keyboard_animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.keyboard_animation.start()
    
    def show_left_click(self):
        """显示左键图片"""
        self.hide_click_images()  # 先隐藏其他按键图片
        if self.left_click_label.pixmap() and not self.left_click_label.pixmap().isNull():
            self.left_click_label.show()
    
    def show_right_click(self):
        """显示右键图片"""
        self.hide_click_images()  # 先隐藏其他按键图片
        if self.right_click_label.pixmap() and not self.right_click_label.pixmap().isNull():
            self.right_click_label.show()
    
    def hide_click_images(self):
        """隐藏所有鼠标按键图片"""
        self.left_click_label.hide()
        self.right_click_label.hide()
    
    def update_mouse_position(self):
        """更新鼠标同步移动（带突变过滤和平滑处理）"""
        # 如果鼠标被锁定，不更新位置
        if self.mouse_locked:
            return
        
        current_pos = QCursor.pos()
        delta_x = current_pos.x() - self.last_mouse_pos.x()
        delta_y = current_pos.y() - self.last_mouse_pos.y()
        
        # 计算移动距离
        distance = (delta_x ** 2 + delta_y ** 2) ** 0.5
        
        # 过滤突变：如果移动距离超过阈值，视为游戏重置鼠标位置，忽略此次移动
        if distance > self.mouse_jump_threshold:
            # 更新最后位置但不应用移动
            self.last_mouse_pos = current_pos
            return
        
        # 使用速度平滑算法，避免抽搐
        # 计算目标速度
        target_velocity_x = delta_x * self.mouse_sensitivity
        target_velocity_y = delta_y * self.mouse_sensitivity
        
        # 平滑过渡到目标速度
        self.mouse_velocity_x += (target_velocity_x - self.mouse_velocity_x) * self.velocity_smoothing
        self.mouse_velocity_y += (target_velocity_y - self.mouse_velocity_y) * self.velocity_smoothing
        
        # 应用平滑后的速度
        self.mouse_offset_x += self.mouse_velocity_x
        self.mouse_offset_y += self.mouse_velocity_y
        
        # 限制偏移范围
        self.mouse_offset_x = max(-self.max_mouse_offset, min(self.max_mouse_offset, self.mouse_offset_x))
        self.mouse_offset_y = max(-self.max_mouse_offset, min(self.max_mouse_offset, self.mouse_offset_y))
        
        # 应用偏移（加上基础偏移）
        base_x = self.settings.get('mouse_x')
        base_y = self.settings.get('mouse_y')
        mouse_width = self.settings.get('mouse_width')
        mouse_height = self.settings.get('mouse_height')
        new_x = int(base_x + self.mouse_offset_x)
        new_y = int(base_y + self.mouse_offset_y)
        
        self.mouse_label.setGeometry(new_x, new_y, mouse_width, mouse_height)
        
        # 同步左右键图片位置
        self.left_click_label.setGeometry(new_x, new_y, mouse_width, mouse_height)
        self.right_click_label.setGeometry(new_x, new_y, mouse_width, mouse_height)
        
        # 缓慢回归中心
        self.mouse_offset_x *= 0.95
        self.mouse_offset_y *= 0.95
        
        # 速度衰减（回归中心时速度也要衰减）
        self.mouse_velocity_x *= 0.95
        self.mouse_velocity_y *= 0.95
        
        self.last_mouse_pos = current_pos

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 应用新设置
            self.apply_settings()
    
    def show_about(self):
        """显示关于对话框"""
        about_text = """
<h2>枝江小馒头 v1.1.0</h2>
<p><b>By：</b>Evelynal</p>
<p><b>B站：</b><a href="https://space.bilibili.com/33374590">伊芙琳娜</a></p>
<p><b>开源地址：</b><a href="https://github.com/Evelynall/ASoul-Little-Bun/">ASoul-Little-Bun</a></p>
<br>
<p><b>免责声明：</b></p>
<p>此工具为粉丝自发制作的非营利性第三方工具，与A-SOUL、枝江娱乐、乐华娱乐等官方无任何关联。</p>
<p>成员Q版形象版权归原作者所有。如有侵权，请联系我们删除。</p>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("关于")
        msg_box.setText(about_text)
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setIcon(QMessageBox.Icon.Information)
        
        # 设置对话框大小
        msg_box.setMinimumWidth(400)
        
        # 使链接可点击
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        
        msg_box.exec()
    
    def apply_settings(self):
        """应用设置"""
        # 更新窗口大小
        self.window_width = self.settings.get('window_width')
        self.window_height = self.settings.get('window_height')
        self.resize(self.window_width, self.window_height)
        
        # 更新鼠标相关参数
        self.max_mouse_offset = self.settings.get('max_mouse_offset')
        self.mouse_sensitivity = self.settings.get('mouse_sensitivity')
        
        # 重新加载图片以应用新的位置
        self.load_character_images()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def contextMenuEvent(self, event):
        """右键菜单"""
        menu = QMenu(self)
        
        # 最小化到托盘
        minimize_action = QAction('最小化到托盘', self)
        minimize_action.triggered.connect(self.hide)
        menu.addAction(minimize_action)
        
        menu.addSeparator()
        
        # 窗口设置二级菜单
        window_settings_menu = menu.addMenu('窗口设置')
        
        # 置顶开关
        always_on_top_action = QAction('窗口置顶', self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        window_settings_menu.addAction(always_on_top_action)
        
        # 鼠标穿透开关
        mouse_passthrough_action = QAction('鼠标穿透', self)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.toggle_mouse_passthrough)
        window_settings_menu.addAction(mouse_passthrough_action)
        
        # 隐藏任务栏开关
        hide_taskbar_action = QAction('隐藏任务栏 (OBS不可识别)', self)
        hide_taskbar_action.setCheckable(True)
        hide_taskbar_action.setChecked(self.hide_taskbar)
        hide_taskbar_action.triggered.connect(self.toggle_hide_taskbar)
        window_settings_menu.addAction(hide_taskbar_action)
        
        menu.addSeparator()
        
        # 锁定鼠标开关
        mouse_locked_action = QAction('锁定鼠标', self)
        mouse_locked_action.setCheckable(True)
        mouse_locked_action.setChecked(self.mouse_locked)
        mouse_locked_action.triggered.connect(self.toggle_mouse_locked)
        menu.addAction(mouse_locked_action)
        
        menu.addSeparator()
        
        # 切换角色二级菜单
        if self.characters:
            character_menu = menu.addMenu('切换角色')
            for character in self.characters.keys():
                char_action = QAction(character, self)
                char_action.triggered.connect(lambda checked, c=character: self.switch_to_character(c))
                character_menu.addAction(char_action)
            
            menu.addSeparator()
        
        # 设置菜单
        settings_action = QAction('设置', self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # 退出菜单
        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        menu.addAction(exit_action)
        
        menu.exec(event.globalPos())
    
    def hide_from_taskbar(self):
        """Windows特定方法：隐藏任务栏图标但保持窗口可被OBS识别"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # 获取窗口句柄
            hwnd = int(self.winId())
            
            # Windows API常量
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            # 获取当前扩展样式
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # 添加WS_EX_TOOLWINDOW并移除WS_EX_APPWINDOW来隐藏任务栏图标
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            
            # 应用新的扩展样式
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # 强制更新窗口显示
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            
        except Exception as e:
            print(f"隐藏任务栏图标失败: {e}")
            # 如果Windows API调用失败，回退到Qt方法
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    
    def show_in_taskbar(self):
        """Windows特定方法：显示任务栏图标以便OBS识别"""
        try:
            import ctypes
            from ctypes import wintypes
            
            # 获取窗口句柄
            hwnd = int(self.winId())
            
            # Windows API常量
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            # 获取当前扩展样式
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            
            # 移除WS_EX_TOOLWINDOW并添加WS_EX_APPWINDOW来显示任务栏图标
            ex_style &= ~WS_EX_TOOLWINDOW
            ex_style |= WS_EX_APPWINDOW
            
            # 应用新的扩展样式
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # 强制更新窗口显示
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
            
        except Exception as e:
            print(f"显示任务栏图标失败: {e}")
            # 如果Windows API调用失败，回退到Qt方法
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
    
    def apply_hide_taskbar(self):
        """应用隐藏任务栏设置"""
        if self.hide_taskbar:
            self.hide_from_taskbar()
        else:
            self.show_in_taskbar()
    
    def show_first_launch_tip(self):
        """显示首次启动提示（只显示一次）"""
        # 检查是否已经显示过提示
        if not self.global_settings.get('first_launch_tip_shown', False):
            tip_text = """
<h3>OBS 识别提示</h3>
<p>当前默认启用了<b>隐藏任务栏</b>模式，在此模式下 OBS 无法识别此窗口。</p>
<br>
<p><b>如需 OBS 识别窗口，请按以下步骤操作：</b></p>
<p>1. 右键点击窗口或托盘图标，取消勾选<b>"隐藏任务栏"</b>选项</p>
<p>2. 在 OBS 中使用<b>游戏捕获</b>源，选择窗口<b>"ASoul Little Bun"</b></p>
<p>3. 在捕获设置中勾选<b>"允许窗口透明"</b>选项</p>
<br>
<p>此提示仅显示一次。</p>
            """
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("使用提示")
            msg_box.setText(tip_text)
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setMinimumWidth(450)
            
            # 显示对话框
            msg_box.exec()
            
            # 标记为已显示
            self.global_settings.set('first_launch_tip_shown', True)
            self.global_settings.save()
    
    def check_for_updates(self):
        """检查更新"""
        try:
            checker = UpdateChecker()
            # 启动时自动清理本地更新日志文件夹
            checker.clean_local_changelogs()
            # 检查更新，传递 global_settings 以支持跳过版本功能
            checker.check_for_updates(self, self.global_settings)
        except Exception as e:
            print(f"检查更新失败: {e}")
    
    def closeEvent(self, event):
        """关闭事件 - 停止监听器和定时器"""
        # 保存窗口位置到全局配置
        pos = self.pos()
        self.global_settings.set('window_x', pos.x())
        self.global_settings.set('window_y', pos.y())
        self.global_settings.set('last_character', self.current_character)
        self.global_settings.save()
        
        # 停止定时器
        if hasattr(self, 'mouse_timer'):
            self.mouse_timer.stop()
        
        # 停止键盘监听器
        if hasattr(self, 'keyboard_listener'):
            self.keyboard_listener.stop()
        
        # 停止鼠标监听器
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        
        # 停止动画
        if hasattr(self, 'keyboard_animation') and self.keyboard_animation:
            self.keyboard_animation.stop()
        
        # 隐藏托盘图标
        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()
        
        event.accept()
        
        # 强制退出应用
        QApplication.quit()

    def hide_from_taskbar(self):
        """Windows特定方法：隐藏任务栏图标但保持窗口可被OBS识别"""
        try:
            import ctypes
            from ctypes import wintypes

            # 获取窗口句柄
            hwnd = int(self.winId())

            # Windows API常量
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000

            # 获取当前扩展样式
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

            # 添加WS_EX_TOOLWINDOW并移除WS_EX_APPWINDOW来隐藏任务栏图标
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW

            # 应用新的扩展样式
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            # 强制更新窗口显示
            ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW

        except Exception as e:
            print(f"隐藏任务栏图标失败: {e}")
            # 如果Windows API调用失败，回退到Qt方法
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)


if __name__ == '__main__':
    # 设置 OpenGL 渲染以支持 OBS 游戏捕获
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    
    # 配置 OpenGL 表面格式
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)  # OpenGL 3.3
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    fmt.setSamples(4)  # 4x 抗锯齿
    QSurfaceFormat.setDefaultFormat(fmt)
    
    app = QApplication(sys.argv)
    pet = ASoulLittleBun()
    sys.exit(app.exec())

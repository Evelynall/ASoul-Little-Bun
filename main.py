import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu, QDialog, QSystemTrayIcon, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QPainter, QCursor, QAction, QIcon
from pynput import keyboard, mouse
from settings import Settings, GlobalSettings, SettingsDialog


class DesktopPet(QWidget):
    def __init__(self):
        super().__init__()
        # 加载全局设置
        self.global_settings = GlobalSettings()
        
        # 窗口状态设置（默认置顶、不穿透）
        self.always_on_top = self.global_settings.get('always_on_top', True)
        self.mouse_passthrough = self.global_settings.get('mouse_passthrough', False)
        
        self.characters = self.load_characters()
        self.current_character_index = 0
        self.current_character = list(self.characters.keys())[0] if self.characters else None
        
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
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
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
            return
        
        character_folder = os.path.join('img', self.current_character)
        self.settings = Settings(self.current_character, character_folder)
    
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
        if hasattr(self, 'tray_icon') and self.current_character:
            # 使用当前角色的背景图片作为托盘图标
            char_data = self.characters.get(self.current_character)
            if char_data and char_data['bg']:
                pixmap = QPixmap(char_data['bg'])
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
        
        # 窗口状态开关
        # 置顶开关
        always_on_top_action = QAction('窗口置顶', self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        tray_menu.addAction(always_on_top_action)
        
        # 鼠标穿透开关
        mouse_passthrough_action = QAction('鼠标穿透', self)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.toggle_mouse_passthrough)
        tray_menu.addAction(mouse_passthrough_action)
        
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
        # 设置基础窗口属性
        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # 根据设置决定是否置顶
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
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
        
        # 加载新角色的配置
        self.load_character_settings()
        
        # 应用新配置
        self.apply_settings()
        
        # 更新托盘图标
        self.update_tray_icon()
    
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
        """更新鼠标同步移动"""
        current_pos = QCursor.pos()
        delta_x = current_pos.x() - self.last_mouse_pos.x()
        delta_y = current_pos.y() - self.last_mouse_pos.y()
        
        # 更新鼠标偏移，限制在最大范围内
        self.mouse_offset_x += delta_x * self.mouse_sensitivity
        self.mouse_offset_y += delta_y * self.mouse_sensitivity
        
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
<h2>枝江小馒头 v1.0.0</h2>
<p><b>By：</b>Evelynal</p>
<p><b>B站：</b><a href="https://space.bilibili.com/33374590">伊芙琳娜</a></p>
<p><b>开源地址：</b><a href="https://github.com/Evelynall">https://github.com/Evelynall</a></p>
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
        
        # 窗口状态开关
        # 置顶开关
        always_on_top_action = QAction('窗口置顶', self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        menu.addAction(always_on_top_action)
        
        # 鼠标穿透开关
        mouse_passthrough_action = QAction('鼠标穿透', self)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.toggle_mouse_passthrough)
        menu.addAction(mouse_passthrough_action)
        
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec())

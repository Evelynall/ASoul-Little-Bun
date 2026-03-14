import sys
import json
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMenu, QDialog, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QAction, QIcon, QSurfaceFormat
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from pynput import mouse

from settings import GlobalSettings, SettingsDialog
from update_checker import UpdateChecker
from character_manager import CharacterManager
from input_handler import InputHandler, MouseTracker
from tray_manager import TrayManager
from window_manager import WindowManager


class ASoulLittleBun(QOpenGLWidget):
    key_press_signal = pyqtSignal(object)
    key_release_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.key_press_signal.connect(self._on_key_press_signal)
        self.key_release_signal.connect(self._on_key_release_signal)
        
        # 加载全局设置
        self.global_settings = GlobalSettings()
        
        # 初始化窗口管理器
        self.window_manager = WindowManager(self, self.global_settings)
        self.always_on_top = self.window_manager.always_on_top
        self.mouse_passthrough = self.window_manager.mouse_passthrough
        self.hide_taskbar = self.window_manager.hide_taskbar
        self.mouse_locked = self.window_manager.mouse_locked
        self.keyboard_horizontal_offset = self.window_manager.keyboard_horizontal_offset
        
        # 初始化角色管理器
        self.character_manager = CharacterManager()
        self.character_manager.initialize_from_global_settings(self.global_settings)
        
        # 从角色管理器获取设置
        self.settings = self.character_manager.settings
        self.window_width = self.settings.get('window_width')
        self.window_height = self.settings.get('window_height')
        
        # 初始化系统托盘
        self.tray_manager = TrayManager(self)
        self.tray_manager.init_tray()
        
        # 初始化UI
        self.init_ui()
        
        # 初始化输入处理器
        self.input_handler = InputHandler(
            self.settings,
            self._handle_key_press,
            self._handle_key_release,
            self._handle_mouse_click,
            self.keyboard_horizontal_offset
        )
        
        # 初始化鼠标跟踪器
        self.mouse_tracker = MouseTracker(self.settings, self.mouse_locked)
        
        # 启动监听器
        self.input_handler.start_listeners()
        
        # 启动鼠标同步定时器
        self.mouse_timer = QTimer()
        self.mouse_timer.timeout.connect(self._update_mouse_position)
        self.mouse_timer.start(16)  # 约60fps
    
    def init_ui(self):
        """初始化UI"""
        # 设置基础窗口属性
        flags = Qt.WindowType.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop, self.always_on_top)
        self.setWindowTitle("ASoul Little Bun")
        
        # 设置窗口图标
        if self.character_manager.current_character:
            icon_path = f"img/{self.character_manager.current_character}/bgImage.png"
            try:
                self.setWindowIcon(QIcon(icon_path))
            except:
                pass
        
        # 设置窗口大小
        self.resize(self.window_width, self.window_height)
        
        # 设置窗口位置
        self._set_window_position()
        
        # 创建图层标签
        self.bg_label = QLabel(self)
        self.keyboard_label = QLabel(self)
        self.mouse_label = QLabel(self)
        self.left_click_label = QLabel(self)
        self.right_click_label = QLabel(self)
        
        # 加载当前角色图片
        self.load_character_images()
        
        # 应用鼠标穿透设置
        self.window_manager.apply_mouse_passthrough()
        
        # 允许拖动窗口
        self.dragging = False
        self.drag_position = QPoint()
        
        self.show()
        
        # 根据设置决定是否隐藏任务栏
        if self.hide_taskbar:
            self.window_manager.apply_hide_taskbar()
        
        # 显示首次启动提示
        self.window_manager.show_first_launch_tip()
        
        # 检查更新
        QTimer.singleShot(1000, self.check_for_updates)
    
    def _set_window_position(self):
        """设置窗口位置"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        window_x = self.global_settings.get('window_x')
        window_y = self.global_settings.get('window_y')
        
        if window_x is None or window_y is None:
            center_x = (screen_geometry.width() - self.window_width) // 2
            center_y = (screen_geometry.height() - self.window_height) // 2
            self.move(center_x, center_y)
        else:
            self.move(window_x, window_y)
    
    def paintEvent(self, event):
        """重写 paintEvent 以支持 OpenGL 渲染和透明背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()
    
    def load_character_images(self):
        """加载当前角色的图片"""
        labels_dict = {
            'bg': self.bg_label,
            'keyboard': self.keyboard_label,
            'mouse': self.mouse_label,
            'left_click': self.left_click_label,
            'right_click': self.right_click_label
        }
        self.character_manager.load_character_images(labels_dict)
    
    def switch_to_character(self, character_name):
        """切换到指定角色"""
        if self.character_manager.set_character(character_name, self.global_settings):
            self.settings = self.character_manager.settings
            self.apply_settings()
            self.tray_manager.create_tray_menu()
    
    # 输入处理回调
    def _handle_key_press(self, key_identifier):
        """处理按键按下"""
        self.key_press_signal.emit(key_identifier)
    
    def _handle_key_release(self):
        """处理按键释放"""
        self.key_release_signal.emit()
    
    def _handle_mouse_click(self, button, pressed):
        """处理鼠标点击"""
        if pressed:
            if button == mouse.Button.left:
                self.show_left_click()
            elif button == mouse.Button.right:
                self.show_right_click()
        else:
            self.hide_click_images()
    
    def _on_key_press_signal(self, key_identifier):
        """键盘按下信号处理"""
        self.input_handler.animate_key_press(self.keyboard_label, key_identifier)
    
    def _on_key_release_signal(self):
        """键盘释放信号处理"""
        self.input_handler.animate_key_release(self.keyboard_label)
    
    def show_left_click(self):
        """显示左键图片"""
        self.hide_click_images()
        if self.left_click_label.pixmap() and not self.left_click_label.pixmap().isNull():
            self.left_click_label.show()
    
    def show_right_click(self):
        """显示右键图片"""
        self.hide_click_images()
        if self.right_click_label.pixmap() and not self.right_click_label.pixmap().isNull():
            self.right_click_label.show()
    
    def hide_click_images(self):
        """隐藏所有鼠标按键图片"""
        self.left_click_label.hide()
        self.right_click_label.hide()
    
    def _update_mouse_position(self):
        """更新鼠标位置"""
        self.mouse_tracker.update_mouse_position(
            self.mouse_label, 
            self.left_click_label, 
            self.right_click_label
        )
    
    # 窗口管理相关方法
    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.window_manager.toggle_always_on_top()
        self.always_on_top = self.window_manager.always_on_top
        self.tray_manager.create_tray_menu()
    
    def toggle_mouse_passthrough(self):
        """切换鼠标穿透状态"""
        self.window_manager.toggle_mouse_passthrough()
        self.mouse_passthrough = self.window_manager.mouse_passthrough
        self.tray_manager.create_tray_menu()
    
    def toggle_hide_taskbar(self):
        """切换隐藏任务栏状态"""
        self.window_manager.toggle_hide_taskbar()
        self.hide_taskbar = self.window_manager.hide_taskbar
        self.tray_manager.create_tray_menu()
    
    def toggle_mouse_locked(self):
        """切换鼠标锁定状态"""
        self.window_manager.toggle_mouse_locked()
        self.mouse_locked = self.window_manager.mouse_locked
        self.mouse_tracker.set_locked(self.mouse_locked)
        
        # 如果锁定鼠标，重置位置
        if self.mouse_locked:
            base_x = self.settings.get('mouse_x')
            base_y = self.settings.get('mouse_y')
            mouse_width = self.settings.get('mouse_width')
            mouse_height = self.settings.get('mouse_height')
            self.mouse_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
            self.left_click_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
            self.right_click_label.setGeometry(base_x, base_y, mouse_width, mouse_height)
        
        self.tray_manager.create_tray_menu()
    
    def toggle_keyboard_horizontal_offset(self):
        """切换键盘横向偏移状态"""
        self.window_manager.toggle_keyboard_horizontal_offset()
        self.keyboard_horizontal_offset = self.window_manager.keyboard_horizontal_offset
        self.input_handler.keyboard_horizontal_offset = self.keyboard_horizontal_offset
        self.tray_manager.create_tray_menu()
    
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
    
    # 设置和关于
    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_settings()
    
    def show_about(self):
        """显示关于对话框"""
        version = self.get_version()
        about_text = f"""
<h2>枝江小馒头 v{version}</h2>
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
        msg_box.setMinimumWidth(400)
        msg_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        msg_box.exec()
    
    def apply_settings(self):
        """应用设置"""
        self.window_width = self.settings.get('window_width')
        self.window_height = self.settings.get('window_height')
        self.resize(self.window_width, self.window_height)
        
        # 更新鼠标跟踪器设置
        self.mouse_tracker.update_settings(self.settings)
        
        # 重新加载图片
        self.load_character_images()
    
    def get_version(self):
        """从version.json文件读取版本号"""
        try:
            with open('version.json', 'r', encoding='utf-8') as f:
                version_data = json.load(f)
                return version_data.get('version', '1.0.0')
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return '1.0.0'
    
    def check_for_updates(self):
        """检查更新"""
        try:
            checker = UpdateChecker()
            checker.check_for_updates(self, self.global_settings)
        except Exception as e:
            print(f"检查更新失败: {e}")
    
    # 鼠标事件处理
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
        
        # 窗口设置
        self._add_window_settings_menu(menu)
        
        menu.addSeparator()
        
        # 锁定鼠标和键盘偏移
        self._add_input_settings_menu(menu)
        
        menu.addSeparator()
        
        # 切换角色
        self._add_character_menu(menu)
        
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
    
    def _add_window_settings_menu(self, parent_menu):
        """添加窗口设置子菜单"""
        window_settings_menu = parent_menu.addMenu('窗口设置')
        
        always_on_top_action = QAction('窗口置顶', self)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.always_on_top)
        always_on_top_action.triggered.connect(self.toggle_always_on_top)
        window_settings_menu.addAction(always_on_top_action)
        
        mouse_passthrough_action = QAction('鼠标穿透', self)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.toggle_mouse_passthrough)
        window_settings_menu.addAction(mouse_passthrough_action)
        
        hide_taskbar_action = QAction('隐藏任务栏 (OBS不可识别)', self)
        hide_taskbar_action.setCheckable(True)
        hide_taskbar_action.setChecked(self.hide_taskbar)
        hide_taskbar_action.triggered.connect(self.toggle_hide_taskbar)
        window_settings_menu.addAction(hide_taskbar_action)
    
    def _add_input_settings_menu(self, parent_menu):
        """添加输入设置菜单项"""
        mouse_locked_action = QAction('锁定鼠标', self)
        mouse_locked_action.setCheckable(True)
        mouse_locked_action.setChecked(self.mouse_locked)
        mouse_locked_action.triggered.connect(self.toggle_mouse_locked)
        parent_menu.addAction(mouse_locked_action)
        
        keyboard_horizontal_offset_action = QAction('键盘横向偏移', self)
        keyboard_horizontal_offset_action.setCheckable(True)
        keyboard_horizontal_offset_action.setChecked(self.keyboard_horizontal_offset)
        keyboard_horizontal_offset_action.triggered.connect(self.toggle_keyboard_horizontal_offset)
        parent_menu.addAction(keyboard_horizontal_offset_action)
    
    def _add_character_menu(self, parent_menu):
        """添加角色切换子菜单"""
        if self.character_manager.characters:
            character_menu = parent_menu.addMenu('切换角色')
            for character in self.character_manager.characters.keys():
                char_action = QAction(character, self)
                char_action.triggered.connect(
                    lambda checked, c=character: self.switch_to_character(c))
                character_menu.addAction(char_action)
            parent_menu.addSeparator()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 保存窗口位置
        pos = self.pos()
        self.global_settings.set('window_x', pos.x())
        self.global_settings.set('window_y', pos.y())
        self.global_settings.set('last_character', self.character_manager.current_character)
        self.global_settings.save()
        
        # 停止定时器
        if hasattr(self, 'mouse_timer'):
            self.mouse_timer.stop()
        
        # 停止监听器
        self.input_handler.stop_listeners()
        
        # 停止动画
        self.input_handler.stop_animation()
        
        # 隐藏托盘图标
        self.tray_manager.hide()
        
        event.accept()
        QApplication.quit()


if __name__ == '__main__':
    # 设置 OpenGL 渲染以支持 OBS 游戏捕获
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseDesktopOpenGL)
    
    # 配置 OpenGL 表面格式
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    fmt.setSamples(4)
    QSurfaceFormat.setDefaultFormat(fmt)
    
    app = QApplication(sys.argv)
    pet = ASoulLittleBun()
    sys.exit(app.exec())

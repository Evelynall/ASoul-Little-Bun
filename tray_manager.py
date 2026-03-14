import os
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QMessageBox
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtCore import Qt


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, parent_window):
        self.parent = parent_window
        self.tray_icon = None
        
    def init_tray(self):
        """初始化系统托盘"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(None, "系统托盘", "系统不支持托盘功能")
            return False
        
        self.tray_icon = QSystemTrayIcon(self.parent)
        self.update_tray_icon()
        self.create_tray_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
        self.tray_icon.showMessage(
            "桌面宠物",
            "程序已最小化到系统托盘",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        return True
    
    def update_tray_icon(self):
        """更新托盘图标"""
        if not self.tray_icon:
            return
        
        icon_path = 'img/icon.png'
        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            scaled_pixmap = pixmap.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, 
                                         Qt.TransformationMode.SmoothTransformation)
            icon = QIcon(scaled_pixmap)
            self.tray_icon.setIcon(icon)
        else:
            self.tray_icon.setIcon(self.parent.style().standardIcon(
                self.parent.style().StandardPixmap.SP_ComputerIcon))
    
    def create_tray_menu(self):
        """创建托盘菜单"""
        if not self.tray_icon:
            return
        
        tray_menu = QMenu()
        
        # 显示/隐藏窗口
        show_action = QAction("显示/隐藏", self.parent)
        show_action.triggered.connect(self.parent.toggle_window_visibility)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        # 窗口设置二级菜单
        self._add_window_settings_menu(tray_menu)
        
        tray_menu.addSeparator()
        
        # 锁定鼠标开关
        mouse_locked_action = QAction('锁定鼠标', self.parent)
        mouse_locked_action.setCheckable(True)
        mouse_locked_action.setChecked(self.parent.mouse_locked)
        mouse_locked_action.triggered.connect(self.parent.toggle_mouse_locked)
        tray_menu.addAction(mouse_locked_action)
        
        # 键盘横向偏移开关
        keyboard_horizontal_offset_action = QAction('键盘横向偏移', self.parent)
        keyboard_horizontal_offset_action.setCheckable(True)
        keyboard_horizontal_offset_action.setChecked(self.parent.keyboard_horizontal_offset)
        keyboard_horizontal_offset_action.triggered.connect(self.parent.toggle_keyboard_horizontal_offset)
        tray_menu.addAction(keyboard_horizontal_offset_action)
        
        # 按键显示开关
        keypress_display_action = QAction('按键显示', self.parent)
        keypress_display_action.setCheckable(True)
        keypress_display_action.setChecked(self.parent.keypress_display_enabled)
        keypress_display_action.triggered.connect(self.parent.toggle_keypress_display)
        tray_menu.addAction(keypress_display_action)
        
        tray_menu.addSeparator()
        
        # 切换角色菜单
        self._add_character_menu(tray_menu)
        
        # 设置和关于
        settings_action = QAction('设置', self.parent)
        settings_action.triggered.connect(self.parent.open_settings)
        tray_menu.addAction(settings_action)
        
        about_action = QAction('关于', self.parent)
        about_action.triggered.connect(self.parent.show_about)
        tray_menu.addAction(about_action)
        
        tray_menu.addSeparator()
        
        # 退出菜单
        exit_action = QAction('退出', self.parent)
        exit_action.triggered.connect(self.parent.quit_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
    
    def _add_window_settings_menu(self, parent_menu):
        """添加窗口设置子菜单"""
        window_settings_menu = parent_menu.addMenu('窗口设置')
        
        # 置顶开关
        always_on_top_action = QAction('窗口置顶', self.parent)
        always_on_top_action.setCheckable(True)
        always_on_top_action.setChecked(self.parent.always_on_top)
        always_on_top_action.triggered.connect(self.parent.toggle_always_on_top)
        window_settings_menu.addAction(always_on_top_action)
        
        # 鼠标穿透开关
        mouse_passthrough_action = QAction('鼠标穿透', self.parent)
        mouse_passthrough_action.setCheckable(True)
        mouse_passthrough_action.setChecked(self.parent.mouse_passthrough)
        mouse_passthrough_action.triggered.connect(self.parent.toggle_mouse_passthrough)
        window_settings_menu.addAction(mouse_passthrough_action)
        
        # 隐藏任务栏开关
        hide_taskbar_action = QAction('隐藏任务栏 (OBS不可识别)', self.parent)
        hide_taskbar_action.setCheckable(True)
        hide_taskbar_action.setChecked(self.parent.hide_taskbar)
        hide_taskbar_action.triggered.connect(self.parent.toggle_hide_taskbar)
        window_settings_menu.addAction(hide_taskbar_action)
    
    def _add_character_menu(self, parent_menu):
        """添加角色切换子菜单"""
        if hasattr(self.parent, 'character_manager') and self.parent.character_manager.characters:
            character_menu = parent_menu.addMenu('切换角色')
            for character in self.parent.character_manager.characters.keys():
                char_action = QAction(character, self.parent)
                char_action.triggered.connect(
                    lambda checked, c=character: self.parent.switch_to_character(c))
                character_menu.addAction(char_action)
            parent_menu.addSeparator()
    
    def _on_tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.parent.toggle_window_visibility()
    
    def hide(self):
        """隐藏托盘图标"""
        if self.tray_icon:
            self.tray_icon.hide()

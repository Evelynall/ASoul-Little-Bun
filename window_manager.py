from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox


class WindowManager:
    """窗口管理器 - 负责窗口状态管理（置顶、穿透、任务栏等）"""
    
    def __init__(self, window, global_settings):
        self.window = window
        self.global_settings = global_settings
        
        # 窗口状态
        self.always_on_top = global_settings.get('always_on_top', True)
        self.mouse_passthrough = global_settings.get('mouse_passthrough', False)
        self.hide_taskbar = global_settings.get('hide_taskbar', True)
        self.mouse_locked = global_settings.get('mouse_locked', False)
        self.keyboard_horizontal_offset = global_settings.get('keyboard_horizontal_offset', True)
        self.keypress_display_enabled = global_settings.get('keypress_display_enabled', True)
        self.keypress_display_background = global_settings.get('keypress_display_background', False)
    
    def toggle_always_on_top(self):
        """切换窗口置顶状态"""
        self.always_on_top = not self.always_on_top
        self.global_settings.set('always_on_top', self.always_on_top)
        self.global_settings.save()
        
        flags = Qt.WindowType.FramelessWindowHint
        if self.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
            
        self.window.setWindowFlags(flags)
        self.window.show()
        
        # 使用QTimer延迟重新应用任务栏设置，确保窗口完全显示后再应用
        if self.hide_taskbar:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, self._hide_from_taskbar)
    
    def toggle_mouse_passthrough(self):
        """切换鼠标穿透状态"""
        self.mouse_passthrough = not self.mouse_passthrough
        self.global_settings.set('mouse_passthrough', self.mouse_passthrough)
        self.global_settings.save()
        self.apply_mouse_passthrough()
        
        # 如果开启了鼠标穿透，显示提示
        if self.mouse_passthrough:
            self._show_mouse_passthrough_tip()
    
    def toggle_hide_taskbar(self):
        """切换隐藏任务栏状态"""
        if not self.hide_taskbar:
            reply = QMessageBox.question(
                self.window, 
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
        self.apply_hide_taskbar()
    
    def toggle_mouse_locked(self):
        """切换鼠标锁定状态"""
        self.mouse_locked = not self.mouse_locked
        self.global_settings.set('mouse_locked', self.mouse_locked)
        self.global_settings.save()
    
    def toggle_keyboard_horizontal_offset(self):
        """切换键盘横向偏移状态"""
        self.keyboard_horizontal_offset = not self.keyboard_horizontal_offset
        self.global_settings.set('keyboard_horizontal_offset', self.keyboard_horizontal_offset)
        self.global_settings.save()
    
    def toggle_keypress_display(self):
        """切换按键显示状态"""
        self.keypress_display_enabled = not self.keypress_display_enabled
        self.global_settings.set('keypress_display_enabled', self.keypress_display_enabled)
        self.global_settings.save()
    
    def toggle_keypress_display_background(self):
        """切换按键背景显示状态"""
        self.keypress_display_background = not self.keypress_display_background
        self.global_settings.set('keypress_display_background', self.keypress_display_background)
        self.global_settings.save()
    
    def apply_mouse_passthrough(self):
        """应用鼠标穿透设置"""
        if self.mouse_passthrough:
            self.window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            for child in self.window.findChildren(object):
                if hasattr(child, 'setAttribute'):
                    child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            
            current_flags = self.window.windowFlags()
            self.window.setWindowFlags(current_flags | Qt.WindowType.WindowTransparentForInput)
            self.window.show()
        else:
            self.window.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            for child in self.window.findChildren(object):
                if hasattr(child, 'setAttribute'):
                    child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            
            current_flags = self.window.windowFlags()
            self.window.setWindowFlags(current_flags & ~Qt.WindowType.WindowTransparentForInput)
            self.window.show()
        
        # 使用QTimer延迟重新应用任务栏设置，确保窗口完全显示后再应用
        if self.hide_taskbar:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, self._hide_from_taskbar)
    
    def apply_hide_taskbar(self):
        """应用隐藏任务栏设置"""
        if self.hide_taskbar:
            self._hide_from_taskbar()
        else:
            self._show_in_taskbar()
    
    def _hide_from_taskbar(self):
        """Windows特定方法：隐藏任务栏图标"""
        try:
            import ctypes
            hwnd = int(self.window.winId())
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW
            ex_style &= ~WS_EX_APPWINDOW
            
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            ctypes.windll.user32.ShowWindow(hwnd, 5)
        except Exception as e:
            print(f"隐藏任务栏图标失败: {e}")
            self.window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    
    def _show_in_taskbar(self):
        """Windows特定方法：显示任务栏图标"""
        try:
            import ctypes
            hwnd = int(self.window.winId())
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style &= ~WS_EX_TOOLWINDOW
            ex_style |= WS_EX_APPWINDOW
            
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            ctypes.windll.user32.ShowWindow(hwnd, 5)
        except Exception as e:
            print(f"显示任务栏图标失败: {e}")
            self.window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
    
    def show_first_launch_tip(self):
        """显示首次启动提示"""
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
            
            msg_box = QMessageBox(self.window)
            msg_box.setWindowTitle("使用提示")
            msg_box.setText(tip_text)
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setMinimumWidth(450)
            msg_box.exec()
            
            self.global_settings.set('first_launch_tip_shown', True)
            self.global_settings.save()

    def _show_mouse_passthrough_tip(self):
        """显示鼠标穿透开启提示"""
        tip_text = """
<h3>鼠标穿透已开启</h3>
<p>鼠标穿透功能已启用，窗口将不再响应鼠标操作。</p>
<br>
<p><b>如需关闭鼠标穿透，请：</b></p>
<p>1. 右键点击<b>系统托盘</b>中的程序图标</p>
<p>2. 在菜单中取消勾选<b>"鼠标穿透"</b>选项</p>
<br>
        """
        
        msg_box = QMessageBox(self.window)
        msg_box.setWindowTitle("鼠标穿透提示")
        msg_box.setText(tip_text)
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setMinimumWidth(400)
        
        # 确保对话框在最前面且不受鼠标穿透影响
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        msg_box.exec()

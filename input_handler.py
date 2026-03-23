from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QCursor
from pynput import keyboard, mouse


class InputHandler:
    """输入处理器 - 负责键盘和鼠标的监听和动画"""
    
    # 键盘布局映射
    KEYBOARD_LAYOUT_UNITS = {
        '`': -1.5, '1': -0.5, '2': 0.5, '3': 1.5, '4': 2.5, '5': 3.5, '6': 4.5,
        '7': 5.5, '8': 6.5, '9': 7.5, '0': 8.5, '-': 9.5, '=': 10.5,
        'q': -0.5, 'w': 0.5, 'e': 1.5, 'r': 2.5, 't': 3.5, 'y': 4.5, 'u': 5.5,
        'i': 6.5, 'o': 7.5, 'p': 8.5, '[': 9.5, ']': 10.5, '\\': 11.5,
        'a': 0.0, 's': 1.0, 'd': 2.0, 'f': 3.0, 'g': 4.0, 'h': 5.0, 'j': 6.0,
        'k': 7.0, 'l': 8.0, ';': 9.0, "'": 10.0,
        'z': -0.5, 'x': 0.5, 'c': 1.5, 'v': 2.5, 'b': 3.5, 'n': 4.5, 'm': 5.5,
        ',': 6.5, '.': 7.5, '/': 8.5,
    }
    
    SPECIAL_KEYBOARD_UNITS = {
        'esc': -1.5, 'tab': -1.0, 'caps_lock': -1.0, 'shift': -1.5,
        'shift_l': -1.5, 'shift_r': 8.5, 'ctrl': -1.5, 'ctrl_l': -1.5,
        'ctrl_r': 7.5, 'alt': 2.5, 'alt_l': 2.5, 'alt_r': 6.5,
        'alt_gr': 6.5, 'cmd': 1.5, 'cmd_l': 1.5, 'cmd_r': 7.0,
        'super': 1.5, 'space': 4.0, 'enter': 9.5, 'backspace': 10.5,
        'delete': 10.5, 'up': 8.0, 'down': 8.0, 'left': 7.0, 'right': 9.0,
    }
    
    KEYBOARD_TRAVEL_REFERENCE = 8.0
    
    def __init__(self, settings, key_press_callback, key_release_callback, 
                 mouse_click_callback, keyboard_horizontal_offset=True):
        self.settings = settings
        self.key_press_callback = key_press_callback
        self.key_release_callback = key_release_callback
        self.mouse_click_callback = mouse_click_callback
        self.keyboard_horizontal_offset = keyboard_horizontal_offset
        
        # 键盘动画相关
        self.keyboard_target_x = None
        self.keyboard_animation = None
        
        # 监听器
        self.keyboard_listener = None
        self.mouse_listener = None
    
    def start_listeners(self):
        """启动键盘和鼠标监听器"""
        # 先停止现有的监听器，避免重复启动
        self.stop_listeners()
        
        # 键盘监听
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
        
        # 鼠标监听
        self.mouse_listener = mouse.Listener(
            on_click=self._on_mouse_click
        )
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
    
    def stop_listeners(self):
        """停止监听器"""
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
            except:
                pass  # 忽略停止时的异常
            self.keyboard_listener = None
            
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except:
                pass  # 忽略停止时的异常
            self.mouse_listener = None
    
    def _on_key_press(self, key):
        """键盘按下事件"""
        key_identifier = self.get_key_identifier(key)
        self.key_press_callback(key_identifier)
    
    def _on_key_release(self, key):
        """键盘释放事件"""
        self.key_release_callback()
    
    def _on_mouse_click(self, x, y, button, pressed):
        """鼠标点击事件"""
        self.mouse_click_callback(button, pressed)
    
    @staticmethod
    def get_key_identifier(key):
        """标准化按键标识符"""
        key_char = getattr(key, 'char', None)
        if key_char:
            return key_char.lower()

        key_name = getattr(key, 'name', None)
        if key_name:
            return key_name.lower()

        key_text = str(key)
        if key_text.startswith('Key.'):
            return key_text.split('.', 1)[1].lower()

        return None
    
    def get_keyboard_target_x(self, key_identifier):
        """根据按键计算键盘横向位置"""
        base_x = self.settings.get('keyboard_x')
        current_target_x = self.keyboard_target_x if self.keyboard_target_x is not None else base_x

        # 如果键盘横向偏移功能关闭，直接返回基础位置
        if not self.keyboard_horizontal_offset:
            return base_x

        if not key_identifier:
            return current_target_x

        key_unit = self.KEYBOARD_LAYOUT_UNITS.get(key_identifier)
        if key_unit is None:
            key_unit = self.SPECIAL_KEYBOARD_UNITS.get(key_identifier)

        if key_unit is None:
            return current_target_x

        horizontal_travel = self.settings.get('keyboard_horizontal_travel', 10)
        target_offset = horizontal_travel * (key_unit / self.KEYBOARD_TRAVEL_REFERENCE)
        return int(round(base_x + target_offset))
    
    def animate_key_press(self, keyboard_label, key_identifier=None):
        """键盘按下动画"""
        if self.keyboard_animation and self.keyboard_animation.state() == QPropertyAnimation.State.Running:
            self.keyboard_animation.stop()
        
        kb_y = self.settings.get('keyboard_y')
        press_offset = self.settings.get('keyboard_press_offset')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        self.keyboard_target_x = self.get_keyboard_target_x(key_identifier)
        
        # 检查配置是否正确
        if press_offset is None or press_offset <= 0:
            press_offset = 5
        
        self.keyboard_animation = QPropertyAnimation(keyboard_label, b"geometry")
        self.keyboard_animation.setDuration(50)
        self.keyboard_animation.setStartValue(keyboard_label.geometry())
        self.keyboard_animation.setEndValue(QRect(self.keyboard_target_x, kb_y + press_offset, kb_width, kb_height))
        self.keyboard_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.keyboard_animation.start()
    
    def animate_key_release(self, keyboard_label):
        """键盘释放动画"""
        if self.keyboard_animation and self.keyboard_animation.state() == QPropertyAnimation.State.Running:
            self.keyboard_animation.stop()
        
        kb_x = self.settings.get('keyboard_x')
        kb_y = self.settings.get('keyboard_y')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        self.keyboard_target_x = kb_x
        
        self.keyboard_animation = QPropertyAnimation(keyboard_label, b"geometry")
        self.keyboard_animation.setDuration(100)
        self.keyboard_animation.setStartValue(keyboard_label.geometry())
        self.keyboard_animation.setEndValue(QRect(kb_x, kb_y, kb_width, kb_height))
        self.keyboard_animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        self.keyboard_animation.start()
    
    def stop_animation(self):
        """停止动画"""
        if self.keyboard_animation:
            self.keyboard_animation.stop()


class MouseTracker:
    """鼠标跟踪器 - 负责鼠标位置同步"""

    def __init__(self, settings, mouse_locked=False):
        self.settings = settings
        self.mouse_locked = mouse_locked

        # 鼠标同步移动相关
        self.last_mouse_pos = QCursor.pos()
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.max_mouse_offset = settings.get('max_mouse_offset')
        self.mouse_sensitivity = settings.get('mouse_sensitivity')

        # 鼠标回正速度（从设置中读取）
        self.mouse_return_speed = settings.get('mouse_return_speed', 0.05)

        # 鼠标位置突变过滤相关
        self.mouse_jump_threshold = 100
        self.mouse_velocity_x = 0
        self.mouse_velocity_y = 0
        self.velocity_smoothing = 0.3
    
    def update_settings(self, settings):
        """更新设置"""
        self.settings = settings
        self.max_mouse_offset = settings.get('max_mouse_offset')
        self.mouse_sensitivity = settings.get('mouse_sensitivity')
        self.mouse_return_speed = settings.get('mouse_return_speed', 0.05)
    
    def set_locked(self, locked):
        """设置鼠标锁定状态"""
        self.mouse_locked = locked
        if locked:
            self.reset_position()
    
    def reset_position(self):
        """重置鼠标位置到中心"""
        self.mouse_offset_x = 0
        self.mouse_offset_y = 0
        self.mouse_velocity_x = 0
        self.mouse_velocity_y = 0
    
    def update_mouse_position(self, mouse_label, left_click_label, right_click_label):
        """更新鼠标同步移动（带突变过滤和平滑处理）"""
        if self.mouse_locked:
            return
        
        current_pos = QCursor.pos()
        delta_x = current_pos.x() - self.last_mouse_pos.x()
        delta_y = current_pos.y() - self.last_mouse_pos.y()
        
        # 计算移动距离
        distance = (delta_x ** 2 + delta_y ** 2) ** 0.5
        
        # 过滤突变
        if distance > self.mouse_jump_threshold:
            self.last_mouse_pos = current_pos
            return
        
        # 速度平滑算法
        target_velocity_x = delta_x * self.mouse_sensitivity
        target_velocity_y = delta_y * self.mouse_sensitivity
        
        self.mouse_velocity_x += (target_velocity_x - self.mouse_velocity_x) * self.velocity_smoothing
        self.mouse_velocity_y += (target_velocity_y - self.mouse_velocity_y) * self.velocity_smoothing
        
        # 应用平滑后的速度
        self.mouse_offset_x += self.mouse_velocity_x
        self.mouse_offset_y += self.mouse_velocity_y
        
        # 限制偏移范围
        self.mouse_offset_x = max(-self.max_mouse_offset, min(self.max_mouse_offset, self.mouse_offset_x))
        self.mouse_offset_y = max(-self.max_mouse_offset, min(self.max_mouse_offset, self.mouse_offset_y))
        
        # 应用偏移
        base_x = self.settings.get('mouse_x')
        base_y = self.settings.get('mouse_y')
        mouse_width = self.settings.get('mouse_width')
        mouse_height = self.settings.get('mouse_height')
        new_x = int(base_x + self.mouse_offset_x)
        new_y = int(base_y + self.mouse_offset_y)
        
        mouse_label.setGeometry(new_x, new_y, mouse_width, mouse_height)
        left_click_label.setGeometry(new_x, new_y, mouse_width, mouse_height)
        right_click_label.setGeometry(new_x, new_y, mouse_width, mouse_height)

        # 缓慢回归中心（使用可配置的回正速度）
        return_factor = 1.0 - self.mouse_return_speed
        self.mouse_offset_x *= return_factor
        self.mouse_offset_y *= return_factor
        self.mouse_velocity_x *= return_factor
        self.mouse_velocity_y *= return_factor

        self.last_mouse_pos = current_pos

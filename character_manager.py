import os
from PyQt6.QtGui import QPixmap
from settings import Settings
from path_manager import path_manager


class CharacterManager:
    """角色管理器 - 负责角色的加载、切换和图片管理"""
    
    def __init__(self, img_dir='img'):
        # 使用路径管理器获取img目录的绝对路径
        if not os.path.isabs(img_dir):
            self.img_dir = path_manager.get_img_dir()
        else:
            self.img_dir = img_dir
        self.characters = {}
        self.current_character = None
        self.current_character_index = 0
        self.settings = None
        
    def load_characters(self):
        """自动识别img目录下的角色文件夹"""
        characters = {}
        
        if not os.path.exists(self.img_dir):
            return characters
        
        for folder in os.listdir(self.img_dir):
            folder_path = os.path.join(self.img_dir, folder)
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
        
        self.characters = characters
        return characters
    
    def set_character(self, character_name, global_settings=None):
        """设置当前角色"""
        if character_name not in self.characters:
            return False
        
        self.current_character = character_name
        character_list = list(self.characters.keys())
        self.current_character_index = character_list.index(character_name)
        
        # 加载角色配置
        self.load_character_settings()
        
        # 保存到全局配置
        if global_settings:
            global_settings.set('last_character', character_name)
            global_settings.save()
        
        return True
    
    def load_character_settings(self):
        """加载当前角色的配置"""
        if not self.current_character:
            self.settings = Settings('default', self.img_dir)
            return
        
        character_folder = os.path.join(self.img_dir, self.current_character)
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
    
    def load_character_images(self, labels_dict):
        """加载当前角色的图片到指定的标签
        
        Args:
            labels_dict: 包含各个标签的字典 {
                'bg': QLabel,
                'keyboard': QLabel,
                'mouse': QLabel,
                'left_click': QLabel,
                'right_click': QLabel
            }
        """
        if not self.current_character or self.current_character not in self.characters:
            return
        
        char_data = self.characters[self.current_character]
        
        # 加载背景图片
        bg_pixmap = QPixmap(char_data['bg'])
        labels_dict['bg'].setPixmap(bg_pixmap)
        bg_width = self.settings.get('bg_width')
        bg_height = self.settings.get('bg_height')
        labels_dict['bg'].setGeometry(0, 0, bg_width, bg_height)
        labels_dict['bg'].setScaledContents(True)
        
        # 加载键盘图片
        keyboard_pixmap = QPixmap(char_data['keyboard'])
        labels_dict['keyboard'].setPixmap(keyboard_pixmap)
        kb_x = self.settings.get('keyboard_x')
        kb_y = self.settings.get('keyboard_y')
        kb_width = self.settings.get('keyboard_width')
        kb_height = self.settings.get('keyboard_height')
        labels_dict['keyboard'].setGeometry(kb_x, kb_y, kb_width, kb_height)
        labels_dict['keyboard'].setScaledContents(True)
        
        # 加载鼠标图片
        mouse_pixmap = QPixmap(char_data['mouse'])
        labels_dict['mouse'].setPixmap(mouse_pixmap)
        mouse_x = self.settings.get('mouse_x')
        mouse_y = self.settings.get('mouse_y')
        mouse_width = self.settings.get('mouse_width')
        mouse_height = self.settings.get('mouse_height')
        labels_dict['mouse'].setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
        labels_dict['mouse'].setScaledContents(True)
        
        # 加载左键图片（初始隐藏）
        if char_data['left_click'] and os.path.exists(char_data['left_click']):
            left_click_pixmap = QPixmap(char_data['left_click'])
            labels_dict['left_click'].setPixmap(left_click_pixmap)
            labels_dict['left_click'].setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
            labels_dict['left_click'].setScaledContents(True)
        labels_dict['left_click'].hide()
        
        # 加载右键图片（初始隐藏）
        if char_data['right_click'] and os.path.exists(char_data['right_click']):
            right_click_pixmap = QPixmap(char_data['right_click'])
            labels_dict['right_click'].setPixmap(right_click_pixmap)
            labels_dict['right_click'].setGeometry(mouse_x, mouse_y, mouse_width, mouse_height)
            labels_dict['right_click'].setScaledContents(True)
        labels_dict['right_click'].hide()
        
        return kb_x  # 返回键盘初始X位置
    
    def initialize_from_global_settings(self, global_settings):
        """从全局设置初始化角色"""
        self.load_characters()
        
        # 加载上次使用的角色
        last_character = global_settings.get('last_character')
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
                self.current_character_index = 0
                self.current_character = None
        
        # 加载当前角色的配置
        self.load_character_settings()

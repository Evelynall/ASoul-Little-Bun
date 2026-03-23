import os
import json
from path_manager import path_manager


class CustomLayer:
    """自定义图层类"""

    def __init__(self, name="", image_path="", x=0, y=0, width=100, height=100,
                 follow_type="none", opacity=1.0, visible=True, z_index=0):
        self.name = name
        self.image_path = image_path
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.follow_type = follow_type
        self.opacity = opacity
        self.visible = visible
        self.z_index = z_index

    def to_dict(self):
        return {
            'name': self.name,
            'image_path': self.image_path,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'follow_type': self.follow_type,
            'opacity': self.opacity,
            'visible': self.visible,
            'z_index': self.z_index,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class DefaultLayer:
    """默认图层（不可删除，图片可替换）"""

    def __init__(self, name, layer_key, z_index=0, opacity=1.0, visible=True):
        self.name = name
        self.layer_key = layer_key
        self.z_index = z_index
        self.opacity = opacity
        self.visible = visible
        self.is_default = True

    def to_dict(self):
        return {
            'layer_key': self.layer_key,
            'z_index': self.z_index,
            'opacity': self.opacity,
            'visible': self.visible,
        }


class CustomLayerManager:
    """自定义图层管理器"""

    def __init__(self, character_name=None):
        self.character_name = character_name
        self.layers = []
        self.config_file = self._get_config_file()
        self.load_layers()

    def _get_config_file(self):
        if self.character_name:
            return path_manager.get_custom_layers_file(self.character_name)
        return path_manager.get_custom_layers_file()

    def load_layers(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.layers = [CustomLayer.from_dict(d) for d in data]
            except Exception as e:
                print(f"加载自定义图层配置失败: {e}")
                self.layers = []
        else:
            self.layers = []

    def save_layers(self):
        try:
            config_dir = os.path.dirname(self.config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump([l.to_dict() for l in self.layers], f,
                          ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存自定义图层配置失败: {e}")

    def get_layers(self):
        return self.layers.copy()

    def get_visible_layers(self):
        return [l for l in self.layers if l.visible]


# 默认图层定义：(name, layer_key, default_z_index)
DEFAULT_LAYER_DEFS = [
    ("背景图", "bg", 0),
    ("手部图层", "keyboard", 1),
    ("鼠标按下图层", "mouse_click", 2),
    ("按键显示", "keypress_display", 3),
]

# config.json 中存储图层顺序和属性的键名
LAYER_ORDER_KEY = 'layer_order'


def load_layer_config(character_name):
    """从角色 config.json 加载图层顺序配置"""
    if not character_name:
        return {}
    config_file = path_manager.get_character_config(character_name)
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return {}


def save_layer_config(character_name, layer_order_data):
    """将图层顺序配置保存到角色 config.json"""
    if not character_name:
        return
    config_file = path_manager.get_character_config(character_name)
    try:
        data = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        # 移除旧的冗余键
        data.pop('default_layers_order', None)

        # 更新配置数据
        # layer_order_data 包含默认图层属性和图层顺序列表
        for key, value in layer_order_data.items():
            data[key] = value

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存图层配置失败: {e}")


def build_all_layers(character_name, custom_layer_manager):
    """
    构建完整有序图层列表（默认图层 + 自定义图层），按保存的顺序排列。
    返回列表即为渲染顺序（index 0 在最底层）。
    """
    saved = load_layer_config(character_name)

    # 构建默认图层对象
    default_map = {}
    for name, key, default_z in DEFAULT_LAYER_DEFS:
        entry = saved.get(key, {})
        layer = DefaultLayer(
            name=name,
            layer_key=key,
            z_index=entry.get('z_index', default_z),
            opacity=entry.get('opacity', 1.0),
            visible=entry.get('visible', True),
        )
        default_map[key] = layer

    # 构建自定义图层对象（深拷贝）
    custom_layers = [CustomLayer.from_dict(l.to_dict()) for l in custom_layer_manager.layers]

    # 检查是否有保存的图层顺序
    layer_order = saved.get('layer_order')
    if layer_order and isinstance(layer_order, list):
        # 按保存的顺序重建图层列表
        ordered_layers = []
        
        # 按保存的顺序添加图层
        for layer_info in layer_order:
            if 'layer_key' in layer_info:
                # 默认图层
                key = layer_info['layer_key']
                if key in default_map:
                    ordered_layers.append(default_map[key])
                    default_map.pop(key)  # 移除已添加的图层
            elif 'name' in layer_info:
                # 自定义图层
                name = layer_info['name']
                for custom_layer in custom_layers[:]:
                    if custom_layer.name == name:
                        ordered_layers.append(custom_layer)
                        custom_layers.remove(custom_layer)
                        break
        
        # 添加任何未在保存顺序中的图层（新增的图层）
        ordered_layers.extend(default_map.values())
        ordered_layers.extend(custom_layers)
        
        all_layers = ordered_layers
    else:
        # 没有保存的顺序，使用默认的 z_index 排序
        all_layers = list(default_map.values()) + custom_layers
        all_layers.sort(key=lambda x: x.z_index)

    # 重新规范化 z_index（确保连续）
    for i, layer in enumerate(all_layers):
        layer.z_index = i

    return all_layers

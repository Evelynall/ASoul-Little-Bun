import os
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QListWidget, QListWidgetItem, QLabel, QSpinBox,
                             QComboBox, QCheckBox, QFileDialog, QMessageBox,
                             QGroupBox, QGridLayout, QSlider, QDoubleSpinBox, QWidget,
                             QScrollArea, QFormLayout, QApplication, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from path_manager import path_manager
from custom_layer_manager import (
    CustomLayer, DefaultLayer, CustomLayerManager,
    DEFAULT_LAYER_DEFS, load_layer_config, save_layer_config,
    build_all_layers,
)


class CustomLayerDialog(QDialog):
    """图层管理对话框（包含默认图层和自定义图层）"""

    layers_changed = pyqtSignal()   # 实时预览信号
    layers_applied = pyqtSignal(object)  # 最终保存信号，携带完整有序图层列表（或 None 表示不保存）
    keypress_preview_requested = pyqtSignal(bool)  # 请求主窗口显示/隐藏按键预览（True=显示，False=隐藏）

    def __init__(self, layer_manager, parent=None, character_name=None, settings=None):
        super().__init__(parent)
        self.layer_manager = layer_manager
        self.character_name = character_name or layer_manager.character_name
        self.settings = settings
        self.current_layer = None
        self.current_index = -1

        # 临时 settings 副本，用于预览
        self.temp_settings = dict(settings.settings) if settings else {}

        # 屏幕尺寸
        screen = QApplication.primaryScreen()
        sg = screen.geometry()
        self.screen_width = sg.width()
        self.screen_height = sg.height()

        # 比例锁定
        self.bg_ratio_locked = True
        self.kb_ratio_locked = True
        self.mouse_ratio_locked = True
        if settings:
            self.bg_ratio = settings.get('bg_width', 240) / max(settings.get('bg_height', 135), 1)
            self.kb_ratio = settings.get('keyboard_width', 25) / max(settings.get('keyboard_height', 25), 1)
            self.mouse_ratio = settings.get('mouse_width', 25) / max(settings.get('mouse_height', 25), 1)
        else:
            self.bg_ratio = 16 / 9
            self.kb_ratio = 1.0
            self.mouse_ratio = 1.0

        # all_layers 是唯一真相来源（列表顺序 = 渲染顺序）
        self.all_layers = build_all_layers(self.character_name, layer_manager)

        # 保存快照，用于 has_unsaved_changes 比较
        self._saved_snapshot = self._make_snapshot()

        self.init_ui()
        self.load_layer_list()

        if not self.all_layers:
            self.set_properties_enabled(False)
            self.clear_layer_properties()

    # ------------------------------------------------------------------
    # 快照工具
    # ------------------------------------------------------------------

    def _make_snapshot(self):
        """生成当前 all_layers 的可比较快照"""
        snap = []
        for layer in self.all_layers:
            if isinstance(layer, DefaultLayer):
                snap.append(('default', layer.layer_key, layer.z_index,
                              layer.opacity, layer.visible))
            else:
                snap.append(('custom', layer.to_dict()))
        return snap

    def _normalize_z_indices(self):
        """将 all_layers 的 z_index 按列表位置重新赋值（0, 1, 2, ...）"""
        for i, layer in enumerate(self.all_layers):
            layer.z_index = i
        order = [f"{i}:{layer.name}" for i, layer in enumerate(self.all_layers)]
        print(f"[图层顺序] {' > '.join(order)}")

    def _is_default_layer(self, layer):
        return isinstance(layer, DefaultLayer)

    # ------------------------------------------------------------------
    # UI 初始化
    # ------------------------------------------------------------------

    def init_ui(self):
        self.setWindowTitle("图层管理")
        self.resize(1000, 680)

        layout = QHBoxLayout(self)

        # 左侧图层列表
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("图层列表（上方=底层，下方=顶层）:"))

        self.layer_list = QListWidget()
        self.layer_list.setMinimumWidth(180)
        self.layer_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.layer_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        self.layer_list.model().rowsMoved.connect(self.on_layer_rows_moved)
        left_layout.addWidget(self.layer_list)

        order_layout = QHBoxLayout()
        self.move_up_btn = QPushButton("↑ 上移")
        self.move_down_btn = QPushButton("↓ 下移")
        self.move_up_btn.clicked.connect(self.move_layer_up)
        self.move_down_btn.clicked.connect(self.move_layer_down)
        order_layout.addWidget(self.move_up_btn)
        order_layout.addWidget(self.move_down_btn)
        left_layout.addLayout(order_layout)

        button_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加图层")
        self.remove_btn = QPushButton("删除图层")
        self.add_btn.clicked.connect(self.add_layer)
        self.remove_btn.clicked.connect(self.remove_layer)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.remove_btn)
        left_layout.addLayout(button_layout)

        layout.addLayout(left_layout, 1)

        # 右侧滚动区域
        right_outer = QVBoxLayout()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        self.right_layout = QVBoxLayout(scroll_content)
        self.right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.create_layer_properties_group(self.right_layout)
        self.create_default_layer_extra_group(self.right_layout)

        scroll.setWidget(scroll_content)
        right_outer.addWidget(scroll)

        # 底部按钮
        bottom_layout = QHBoxLayout()
        self.realtime_preview_check = QCheckBox("实时预览")
        self.realtime_preview_check.setChecked(True)
        bottom_layout.addWidget(self.realtime_preview_check)

        self.reset_default_btn = QPushButton("恢复默认")
        self.reset_default_btn.setToolTip("将图像调整设置恢复为默认值")
        self.reset_default_btn.clicked.connect(self.reset_image_settings_to_default)
        bottom_layout.addWidget(self.reset_default_btn)

        bottom_layout.addStretch()
        self.apply_btn = QPushButton("应用")
        self.close_btn = QPushButton("关闭")
        self.apply_btn.clicked.connect(self.apply_changes)
        self.close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self.apply_btn)
        bottom_layout.addWidget(self.close_btn)
        right_outer.addLayout(bottom_layout)

        layout.addLayout(right_outer, 3)

    def create_layer_properties_group(self, parent_layout):
        self.props_group = QGroupBox("图层属性")
        layout = QGridLayout(self.props_group)

        layout.addWidget(QLabel("名称:"), 0, 0)
        self.name_edit = QLabel("未选择图层")
        layout.addWidget(self.name_edit, 0, 1)

        layout.addWidget(QLabel("图片:"), 1, 0)
        self.image_btn = QPushButton("选择图片")
        self.image_btn.clicked.connect(self.select_image)
        layout.addWidget(self.image_btn, 1, 1)

        layout.addWidget(QLabel("X位置:"), 2, 0)
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-9999, 9999)
        layout.addWidget(self.x_spin, 2, 1)

        layout.addWidget(QLabel("Y位置:"), 3, 0)
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-9999, 9999)
        layout.addWidget(self.y_spin, 3, 1)

        layout.addWidget(QLabel("宽度:"), 4, 0)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 9999)
        layout.addWidget(self.width_spin, 4, 1)

        layout.addWidget(QLabel("高度:"), 5, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 9999)
        layout.addWidget(self.height_spin, 5, 1)

        layout.addWidget(QLabel("跟随:"), 6, 0)
        self.follow_combo = QComboBox()
        self.follow_combo.addItems(["不跟随", "跟随键盘", "跟随鼠标"])
        layout.addWidget(self.follow_combo, 6, 1)

        layout.addWidget(QLabel("透明度:"), 7, 0)
        self.opacity_spin = QDoubleSpinBox()
        self.opacity_spin.setRange(0.0, 1.0)
        self.opacity_spin.setSingleStep(0.1)
        self.opacity_spin.setDecimals(1)
        layout.addWidget(self.opacity_spin, 7, 1)

        self.visible_check = QCheckBox("可见")
        layout.addWidget(self.visible_check, 8, 0, 1, 2)

        layout.addWidget(QLabel("快捷设置:"), 9, 0)
        shortcut_layout = QHBoxLayout()
        self.reset_pos_btn = QPushButton("重置位置")
        self.reset_pos_btn.clicked.connect(self.reset_position)
        shortcut_layout.addWidget(self.reset_pos_btn)
        self.reset_size_btn = QPushButton("重置大小")
        self.reset_size_btn.clicked.connect(self.reset_size)
        shortcut_layout.addWidget(self.reset_size_btn)
        self.semi_transparent_btn = QPushButton("半透明")
        self.semi_transparent_btn.clicked.connect(self.set_semi_transparent)
        shortcut_layout.addWidget(self.semi_transparent_btn)
        shortcut_widget = QWidget()
        shortcut_widget.setLayout(shortcut_layout)
        layout.addWidget(shortcut_widget, 9, 1)

        parent_layout.addWidget(self.props_group)
        self.set_properties_enabled(False)

    def _make_slider_spin_row(self, layout, label, min_val, max_val, default_val,
                               suffix=' px', on_change=None):
        row_layout = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        spin.setSuffix(suffix)
        if on_change:
            slider.valueChanged.connect(on_change)
        else:
            slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        row_layout.addWidget(slider)
        row_layout.addWidget(spin)
        layout.addRow(label, row_layout)
        return slider, spin

    def create_default_layer_extra_group(self, parent_layout):
        self.extra_group = QGroupBox("图像调整")
        extra_layout = QVBoxLayout(self.extra_group)

        s = self.settings
        sw, sh = self.screen_width, self.screen_height

        def sv(key, default):
            return s.get(key, default) if s else default

        # ---- 背景图 ----
        self.bg_extra = QWidget()
        bg_form = QFormLayout(self.bg_extra)

        self.sync_scale_check = QCheckBox("全体同步缩放")
        self.sync_scale_check.setChecked(sv('sync_scale_enabled', False))
        self.sync_scale_check.stateChanged.connect(self._on_sync_scale_changed)
        bg_form.addRow('', self.sync_scale_check)

        self.bg_lock_ratio = QCheckBox("锁定比例")
        self.bg_lock_ratio.setChecked(True)
        self.bg_lock_ratio.stateChanged.connect(self._on_bg_lock_changed)
        bg_form.addRow('', self.bg_lock_ratio)

        self.bg_width_slider, self.bg_width_spin = self._make_slider_spin_row(
            bg_form, '宽度:', 0, sw, sv('bg_width', 240), on_change=self._on_bg_width_changed)
        self.bg_height_slider, self.bg_height_spin = self._make_slider_spin_row(
            bg_form, '高度:', 0, sh, sv('bg_height', 135), on_change=self._on_bg_height_changed)
        extra_layout.addWidget(self.bg_extra)

        # ---- 手部图层 ----
        self.kb_extra = QWidget()
        kb_form = QFormLayout(self.kb_extra)

        self.kb_lock_ratio = QCheckBox("锁定比例")
        self.kb_lock_ratio.setChecked(True)
        self.kb_lock_ratio.stateChanged.connect(self._on_kb_lock_changed)
        kb_form.addRow('', self.kb_lock_ratio)

        self.kb_x_slider, self.kb_x_spin = self._make_slider_spin_row(kb_form, 'X 偏移:', 0, sw, sv('keyboard_x', 94))
        self.kb_y_slider, self.kb_y_spin = self._make_slider_spin_row(kb_form, 'Y 偏移:', 0, sh, sv('keyboard_y', 84))
        self.kb_press_slider, self.kb_press_spin = self._make_slider_spin_row(kb_form, '按下偏移:', 0, sh, sv('keyboard_press_offset', 5))
        self.kb_horizontal_slider, self.kb_horizontal_spin = self._make_slider_spin_row(kb_form, '水平移动范围:', 0, 100, sv('keyboard_horizontal_travel', 50))
        self.kb_width_slider, self.kb_width_spin = self._make_slider_spin_row(kb_form, '宽度:', 0, sw, sv('keyboard_width', 25), on_change=self._on_kb_width_changed)
        self.kb_height_slider, self.kb_height_spin = self._make_slider_spin_row(kb_form, '高度:', 0, sh, sv('keyboard_height', 25), on_change=self._on_kb_height_changed)
        extra_layout.addWidget(self.kb_extra)

        # ---- 鼠标按下图层 ----
        self.mouse_extra = QWidget()
        mouse_form = QFormLayout(self.mouse_extra)

        self.mouse_lock_ratio = QCheckBox("锁定比例")
        self.mouse_lock_ratio.setChecked(True)
        self.mouse_lock_ratio.stateChanged.connect(self._on_mouse_lock_changed)
        mouse_form.addRow('', self.mouse_lock_ratio)

        self.mouse_x_slider, self.mouse_x_spin = self._make_slider_spin_row(mouse_form, 'X 偏移:', 0, sw, sv('mouse_x', 190))
        self.mouse_y_slider, self.mouse_y_spin = self._make_slider_spin_row(mouse_form, 'Y 偏移:', 0, sh, sv('mouse_y', 90))
        self.max_offset_slider, self.max_offset_spin = self._make_slider_spin_row(mouse_form, '最大移动范围:', 0, max(sw, sh), sv('max_mouse_offset', 20))
        self.sensitivity_slider, self.sensitivity_spin = self._make_slider_spin_row(mouse_form, '移动灵敏度:', 0, 1000, int(sv('mouse_sensitivity', 0.3) * 100), suffix=' %')
        self.return_speed_slider, self.return_speed_spin = self._make_slider_spin_row(mouse_form, '回正速度:', 1, 200, int(sv('mouse_return_speed', 0.05) * 1000), suffix=' ‰')
        self.mouse_width_slider, self.mouse_width_spin = self._make_slider_spin_row(mouse_form, '宽度:', 0, sw, sv('mouse_width', 25), on_change=self._on_mouse_width_changed)
        self.mouse_height_slider, self.mouse_height_spin = self._make_slider_spin_row(mouse_form, '高度:', 0, sh, sv('mouse_height', 25), on_change=self._on_mouse_height_changed)
        extra_layout.addWidget(self.mouse_extra)

        # ---- 按键显示 ----
        self.keypress_extra = QWidget()
        keypress_form = QFormLayout(self.keypress_extra)

        self.keypress_enabled_check = QCheckBox("启用按键显示")
        self.keypress_enabled_check.setChecked(sv('keypress_display_enabled', True))
        keypress_form.addRow('', self.keypress_enabled_check)

        self.keypress_x_slider, self.keypress_x_spin = self._make_slider_spin_row(keypress_form, 'X 偏移:', 0, sw, sv('keypress_display_x', 8))
        self.keypress_y_slider, self.keypress_y_spin = self._make_slider_spin_row(keypress_form, 'Y 偏移:', 0, sh, sv('keypress_display_y', 53))
        self.keypress_font_slider, self.keypress_font_spin = self._make_slider_spin_row(keypress_form, '字体大小:', 8, 48, sv('keypress_display_font_size', 20), suffix=' px')
        self.keypress_max_width_slider, self.keypress_max_width_spin = self._make_slider_spin_row(keypress_form, '最大宽度:', 50, sw, sv('keypress_display_max_width', 200), suffix=' px')
        self.keypress_height_slider, self.keypress_height_spin = self._make_slider_spin_row(keypress_form, '高度:', 20, sh, sv('keypress_display_height', 40), suffix=' px')
        extra_layout.addWidget(self.keypress_extra)

        parent_layout.addWidget(self.extra_group)
        self.extra_group.hide()

        self._connect_extra_signals()
        self._init_sync_values()

    def _init_sync_values(self):
        s = self.settings
        def sv(k, d): return s.get(k, d) if s else d
        self.initial_bg_width = sv('bg_width', 240)
        self.initial_bg_height = sv('bg_height', 135)
        self.initial_kb_x = sv('keyboard_x', 94)
        self.initial_kb_y = sv('keyboard_y', 84)
        self.initial_kb_w = sv('keyboard_width', 25)
        self.initial_kb_h = sv('keyboard_height', 25)
        self.initial_mouse_x = sv('mouse_x', 190)
        self.initial_mouse_y = sv('mouse_y', 90)
        self.initial_mouse_w = sv('mouse_width', 25)
        self.initial_mouse_h = sv('mouse_height', 25)
        self.initial_custom_layers = []

    def _connect_extra_signals(self):
        for spin in [self.bg_width_spin, self.bg_height_spin,
                     self.kb_x_spin, self.kb_y_spin, self.kb_press_spin,
                     self.kb_horizontal_spin, self.kb_width_spin, self.kb_height_spin,
                     self.mouse_x_spin, self.mouse_y_spin, self.max_offset_spin,
                     self.sensitivity_spin, self.return_speed_spin, self.mouse_width_spin, self.mouse_height_spin,
                     self.keypress_x_spin, self.keypress_y_spin, self.keypress_font_spin, self.keypress_max_width_spin, self.keypress_height_spin]:
            spin.valueChanged.connect(self._on_extra_changed)
        self.sync_scale_check.stateChanged.connect(self._on_extra_changed)
        self.keypress_enabled_check.stateChanged.connect(self._on_extra_changed)

    def _on_extra_changed(self):
        self.temp_settings['bg_width'] = self.bg_width_spin.value()
        self.temp_settings['bg_height'] = self.bg_height_spin.value()
        self.temp_settings['keyboard_x'] = self.kb_x_spin.value()
        self.temp_settings['keyboard_y'] = self.kb_y_spin.value()
        self.temp_settings['keyboard_press_offset'] = self.kb_press_spin.value()
        self.temp_settings['keyboard_horizontal_travel'] = self.kb_horizontal_spin.value()
        self.temp_settings['keyboard_width'] = self.kb_width_spin.value()
        self.temp_settings['keyboard_height'] = self.kb_height_spin.value()
        self.temp_settings['mouse_x'] = self.mouse_x_spin.value()
        self.temp_settings['mouse_y'] = self.mouse_y_spin.value()
        self.temp_settings['max_mouse_offset'] = self.max_offset_spin.value()
        self.temp_settings['mouse_sensitivity'] = self.sensitivity_spin.value() / 100.0
        self.temp_settings['mouse_return_speed'] = self.return_speed_spin.value() / 1000.0
        self.temp_settings['mouse_width'] = self.mouse_width_spin.value()
        self.temp_settings['mouse_height'] = self.mouse_height_spin.value()
        self.temp_settings['sync_scale_enabled'] = self.sync_scale_check.isChecked()
        self.temp_settings['keypress_display_enabled'] = self.keypress_enabled_check.isChecked()
        self.temp_settings['keypress_display_x'] = self.keypress_x_spin.value()
        self.temp_settings['keypress_display_y'] = self.keypress_y_spin.value()
        self.temp_settings['keypress_display_font_size'] = self.keypress_font_spin.value()
        self.temp_settings['keypress_display_max_width'] = self.keypress_max_width_spin.value()
        self.temp_settings['keypress_display_height'] = self.keypress_height_spin.value()
        max_w = max(self.bg_width_spin.value(),
                    self.kb_width_spin.value() + self.kb_x_spin.value(),
                    self.mouse_width_spin.value() + self.mouse_x_spin.value())
        max_h = max(self.bg_height_spin.value(),
                    self.kb_height_spin.value() + self.kb_y_spin.value(),
                    self.mouse_height_spin.value() + self.mouse_y_spin.value())
        self.temp_settings['window_width'] = max_w
        self.temp_settings['window_height'] = max_h
        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    # 比例锁定回调
    def _on_bg_lock_changed(self, state):
        self.bg_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.bg_ratio_locked:
            self.bg_ratio = self.bg_width_spin.value() / max(self.bg_height_spin.value(), 1)

    def _on_kb_lock_changed(self, state):
        self.kb_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.kb_ratio_locked:
            self.kb_ratio = self.kb_width_spin.value() / max(self.kb_height_spin.value(), 1)

    def _on_mouse_lock_changed(self, state):
        self.mouse_ratio_locked = (state == Qt.CheckState.Checked.value)
        if self.mouse_ratio_locked:
            self.mouse_ratio = self.mouse_width_spin.value() / max(self.mouse_height_spin.value(), 1)

    def _on_sync_scale_changed(self, state):
        if state == Qt.CheckState.Checked.value:
            self.initial_bg_width = self.bg_width_spin.value()
            self.initial_bg_height = self.bg_height_spin.value()
            self.initial_kb_x = self.kb_x_spin.value()
            self.initial_kb_y = self.kb_y_spin.value()
            self.initial_kb_w = self.kb_width_spin.value()
            self.initial_kb_h = self.kb_height_spin.value()
            self.initial_mouse_x = self.mouse_x_spin.value()
            self.initial_mouse_y = self.mouse_y_spin.value()
            self.initial_mouse_w = self.mouse_width_spin.value()
            self.initial_mouse_h = self.mouse_height_spin.value()
            self.initial_custom_layers = [
                {'x': l.x, 'y': l.y, 'width': l.width, 'height': l.height}
                for l in self.all_layers if not self._is_default_layer(l)
            ]

    def _on_bg_width_changed(self, value):
        self.bg_width_spin.setValue(value)
        if self.bg_ratio_locked and value > 0:
            new_h = int(value / self.bg_ratio)
            self.bg_height_slider.blockSignals(True); self.bg_height_spin.blockSignals(True)
            self.bg_height_slider.setValue(new_h); self.bg_height_spin.setValue(new_h)
            self.bg_height_slider.blockSignals(False); self.bg_height_spin.blockSignals(False)
        if self.sync_scale_check.isChecked() and self.initial_bg_width > 0:
            self._sync_all_elements()

    def _on_bg_height_changed(self, value):
        self.bg_height_spin.setValue(value)
        if self.bg_ratio_locked and value > 0:
            new_w = int(value * self.bg_ratio)
            self.bg_width_slider.blockSignals(True); self.bg_width_spin.blockSignals(True)
            self.bg_width_slider.setValue(new_w); self.bg_width_spin.setValue(new_w)
            self.bg_width_slider.blockSignals(False); self.bg_width_spin.blockSignals(False)
        if self.sync_scale_check.isChecked() and self.initial_bg_height > 0:
            self._sync_all_elements()

    def _on_kb_width_changed(self, value):
        self.kb_width_spin.setValue(value)
        if self.kb_ratio_locked and value > 0:
            new_h = int(value / self.kb_ratio)
            self.kb_height_slider.blockSignals(True); self.kb_height_spin.blockSignals(True)
            self.kb_height_slider.setValue(new_h); self.kb_height_spin.setValue(new_h)
            self.kb_height_slider.blockSignals(False); self.kb_height_spin.blockSignals(False)

    def _on_kb_height_changed(self, value):
        self.kb_height_spin.setValue(value)
        if self.kb_ratio_locked and value > 0:
            new_w = int(value * self.kb_ratio)
            self.kb_width_slider.blockSignals(True); self.kb_width_spin.blockSignals(True)
            self.kb_width_slider.setValue(new_w); self.kb_width_spin.setValue(new_w)
            self.kb_width_slider.blockSignals(False); self.kb_width_spin.blockSignals(False)

    def _on_mouse_width_changed(self, value):
        self.mouse_width_spin.setValue(value)
        if self.mouse_ratio_locked and value > 0:
            new_h = int(value / self.mouse_ratio)
            self.mouse_height_slider.blockSignals(True); self.mouse_height_spin.blockSignals(True)
            self.mouse_height_slider.setValue(new_h); self.mouse_height_spin.setValue(new_h)
            self.mouse_height_slider.blockSignals(False); self.mouse_height_spin.blockSignals(False)

    def _on_mouse_height_changed(self, value):
        self.mouse_height_spin.setValue(value)
        if self.mouse_ratio_locked and value > 0:
            new_w = int(value * self.mouse_ratio)
            self.mouse_width_slider.blockSignals(True); self.mouse_width_spin.blockSignals(True)
            self.mouse_width_slider.setValue(new_w); self.mouse_width_spin.setValue(new_w)
            self.mouse_width_slider.blockSignals(False); self.mouse_height_spin.blockSignals(False)

    def _sync_all_elements(self):
        if self.initial_bg_width <= 0 or self.initial_bg_height <= 0:
            return
        sx = self.bg_width_spin.value() / self.initial_bg_width
        sy = self.bg_height_spin.value() / self.initial_bg_height
        for slider, spin, val in [
            (self.kb_x_slider, self.kb_x_spin, int(self.initial_kb_x * sx)),
            (self.kb_y_slider, self.kb_y_spin, int(self.initial_kb_y * sy)),
            (self.kb_width_slider, self.kb_width_spin, int(self.initial_kb_w * sx)),
            (self.kb_height_slider, self.kb_height_spin, int(self.initial_kb_h * sy)),
            (self.mouse_x_slider, self.mouse_x_spin, int(self.initial_mouse_x * sx)),
            (self.mouse_y_slider, self.mouse_y_spin, int(self.initial_mouse_y * sy)),
            (self.mouse_width_slider, self.mouse_width_spin, int(self.initial_mouse_w * sx)),
            (self.mouse_height_slider, self.mouse_height_spin, int(self.initial_mouse_h * sy)),
        ]:
            slider.blockSignals(True); spin.blockSignals(True)
            slider.setValue(val); spin.setValue(val)
            slider.blockSignals(False); spin.blockSignals(False)

        # 同步自定义图层
        initial_customs = getattr(self, 'initial_custom_layers', None)
        if initial_customs:
            custom_layers = [l for l in self.all_layers if not self._is_default_layer(l)]
            for i, layer in enumerate(custom_layers):
                if i < len(initial_customs):
                    init = initial_customs[i]
                    layer.x = int(init['x'] * sx)
                    layer.y = int(init['y'] * sy)
                    layer.width = int(init['width'] * sx)
                    layer.height = int(init['height'] * sy)
            if self.current_layer and not self._is_default_layer(self.current_layer):
                self.disconnect_property_signals()
                self.x_spin.setValue(self.current_layer.x)
                self.y_spin.setValue(self.current_layer.y)
                self.width_spin.setValue(self.current_layer.width)
                self.height_spin.setValue(self.current_layer.height)
                self.connect_property_signals()

        if self.realtime_preview_check.isChecked():
            self._on_extra_changed()

    def _show_extra_for_layer(self, layer_key):
        self.bg_extra.setVisible(layer_key == 'bg')
        self.kb_extra.setVisible(layer_key == 'keyboard')
        self.mouse_extra.setVisible(layer_key == 'mouse_click')
        self.keypress_extra.setVisible(layer_key == 'keypress_display')
        self.extra_group.setVisible(True)

    def reset_image_settings_to_default(self):
        from settings import Settings
        reply = QMessageBox.question(
            self, "确认恢复默认",
            "确定要将所有图像调整设置恢复为默认值吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        defaults = Settings.DEFAULT_SETTINGS
        keys = [
            'window_width', 'window_height', 'bg_width', 'bg_height',
            'keyboard_x', 'keyboard_y', 'keyboard_width', 'keyboard_height',
            'keyboard_press_offset', 'keyboard_horizontal_travel',
            'mouse_x', 'mouse_y', 'mouse_width', 'mouse_height',
            'max_mouse_offset', 'mouse_sensitivity', 'mouse_return_speed', 'sync_scale_enabled',
            'keypress_display_enabled', 'keypress_display_x', 'keypress_display_y',
            'keypress_display_font_size', 'keypress_display_max_width', 'keypress_display_height',
        ]
        for key in keys:
            if key in defaults:
                self.temp_settings[key] = defaults[key]
        if self.current_layer and self._is_default_layer(self.current_layer):
            self._load_extra_panel_values(self.current_layer.layer_key)
        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    # ------------------------------------------------------------------
    # 属性面板
    # ------------------------------------------------------------------

    def set_properties_enabled(self, enabled, is_default=False):
        self.set_properties_enabled_without_signals(enabled, is_default)
        if enabled:
            self.connect_property_signals()
        else:
            self.disconnect_property_signals()

    def set_properties_enabled_without_signals(self, enabled, is_default=False):
        self.image_btn.setEnabled(enabled)
        self.x_spin.setEnabled(enabled and not is_default)
        self.y_spin.setEnabled(enabled and not is_default)
        self.width_spin.setEnabled(enabled and not is_default)
        self.height_spin.setEnabled(enabled and not is_default)
        self.follow_combo.setEnabled(enabled and not is_default)
        self.reset_pos_btn.setEnabled(enabled and not is_default)
        self.reset_size_btn.setEnabled(enabled and not is_default)
        self.opacity_spin.setEnabled(enabled)
        self.visible_check.setEnabled(enabled)
        self.semi_transparent_btn.setEnabled(enabled)
        self.remove_btn.setEnabled(enabled and not is_default)

    def load_layer_list(self):
        self.layer_list.currentRowChanged.disconnect()
        self.layer_list.clear()
        for layer in self.all_layers:
            vis = '可见' if layer.visible else '隐藏'
            if self._is_default_layer(layer):
                text = f"[默认] {layer.name} ({vis})"
            else:
                text = f"{layer.name} ({vis})"
            item = QListWidgetItem(text)
            if self._is_default_layer(layer):
                item.setForeground(Qt.GlobalColor.darkBlue)
            self.layer_list.addItem(item)
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        if not self.all_layers:
            self.layer_list.setCurrentRow(-1)

    def on_layer_selected(self, row):
        if 0 <= row < len(self.all_layers):
            self.disconnect_property_signals()
            self.current_index = row
            self.current_layer = self.all_layers[row]
            is_default = self._is_default_layer(self.current_layer)
            self.set_properties_enabled_without_signals(True, is_default)
            self.load_layer_properties()
            self.connect_property_signals()
            if is_default:
                self._show_extra_for_layer(self.current_layer.layer_key)
                # 选中按键显示图层时，请求主窗口临时显示预览
                self.keypress_preview_requested.emit(
                    self.current_layer.layer_key == 'keypress_display'
                )
            else:
                self.extra_group.hide()
                # 选中非按键显示图层时，取消预览
                self.keypress_preview_requested.emit(False)
        else:
            self.current_index = -1
            self.current_layer = None
            self.set_properties_enabled(False)
            self.clear_layer_properties()
            self.extra_group.hide()
            self.keypress_preview_requested.emit(False)

    def _get_default_layer_display_values(self, layer):
        ts = self.temp_settings
        key = layer.layer_key
        if key == 'bg':
            return 0, 0, ts.get('bg_width', 240), ts.get('bg_height', 135)
        elif key == 'keyboard':
            return (ts.get('keyboard_x', 0), ts.get('keyboard_y', 0),
                    ts.get('keyboard_width', 25), ts.get('keyboard_height', 25))
        elif key == 'mouse_click':
            return (ts.get('mouse_x', 0), ts.get('mouse_y', 0),
                    ts.get('mouse_width', 25), ts.get('mouse_height', 25))
        return 0, 0, 100, 100

    def _load_extra_panel_values(self, layer_key):
        ts = self.temp_settings
        def sv(k, d): return ts.get(k, d)

        if layer_key == 'bg':
            self.bg_width_slider.blockSignals(True); self.bg_width_spin.blockSignals(True)
            self.bg_height_slider.blockSignals(True); self.bg_height_spin.blockSignals(True)
            self.bg_width_slider.setValue(sv('bg_width', 240)); self.bg_width_spin.setValue(sv('bg_width', 240))
            self.bg_height_slider.setValue(sv('bg_height', 135)); self.bg_height_spin.setValue(sv('bg_height', 135))
            self.bg_width_slider.blockSignals(False); self.bg_width_spin.blockSignals(False)
            self.bg_height_slider.blockSignals(False); self.bg_height_spin.blockSignals(False)
            self.sync_scale_check.blockSignals(True)
            self.sync_scale_check.setChecked(sv('sync_scale_enabled', False))
            self.sync_scale_check.blockSignals(False)
        elif layer_key == 'keyboard':
            for slider, spin, key, default in [
                (self.kb_x_slider, self.kb_x_spin, 'keyboard_x', 94),
                (self.kb_y_slider, self.kb_y_spin, 'keyboard_y', 84),
                (self.kb_press_slider, self.kb_press_spin, 'keyboard_press_offset', 5),
                (self.kb_horizontal_slider, self.kb_horizontal_spin, 'keyboard_horizontal_travel', 50),
                (self.kb_width_slider, self.kb_width_spin, 'keyboard_width', 25),
                (self.kb_height_slider, self.kb_height_spin, 'keyboard_height', 25),
            ]:
                slider.blockSignals(True); spin.blockSignals(True)
                slider.setValue(sv(key, default)); spin.setValue(sv(key, default))
                slider.blockSignals(False); spin.blockSignals(False)
        elif layer_key == 'mouse_click':
            for slider, spin, key, default in [
                (self.mouse_x_slider, self.mouse_x_spin, 'mouse_x', 190),
                (self.mouse_y_slider, self.mouse_y_spin, 'mouse_y', 90),
                (self.max_offset_slider, self.max_offset_spin, 'max_mouse_offset', 20),
                (self.mouse_width_slider, self.mouse_width_spin, 'mouse_width', 25),
                (self.mouse_height_slider, self.mouse_height_spin, 'mouse_height', 25),
            ]:
                slider.blockSignals(True); spin.blockSignals(True)
                slider.setValue(sv(key, default)); spin.setValue(sv(key, default))
                slider.blockSignals(False); spin.blockSignals(False)
            self.sensitivity_slider.blockSignals(True); self.sensitivity_spin.blockSignals(True)
            self.sensitivity_slider.setValue(int(sv('mouse_sensitivity', 0.3) * 100))
            self.sensitivity_spin.setValue(int(sv('mouse_sensitivity', 0.3) * 100))
            self.sensitivity_slider.blockSignals(False); self.sensitivity_spin.blockSignals(False)
            self.return_speed_slider.blockSignals(True); self.return_speed_spin.blockSignals(True)
            self.return_speed_slider.setValue(int(sv('mouse_return_speed', 0.05) * 1000))
            self.return_speed_spin.setValue(int(sv('mouse_return_speed', 0.05) * 1000))
            self.return_speed_slider.blockSignals(False); self.return_speed_spin.blockSignals(False)
        elif layer_key == 'keypress_display':
            self.keypress_enabled_check.blockSignals(True)
            self.keypress_enabled_check.setChecked(sv('keypress_display_enabled', True))
            self.keypress_enabled_check.blockSignals(False)
            for slider, spin, key, default in [
                (self.keypress_x_slider, self.keypress_x_spin, 'keypress_display_x', 8),
                (self.keypress_y_slider, self.keypress_y_spin, 'keypress_display_y', 53),
                (self.keypress_font_slider, self.keypress_font_spin, 'keypress_display_font_size', 20),
                (self.keypress_max_width_slider, self.keypress_max_width_spin, 'keypress_display_max_width', 200),
                (self.keypress_height_slider, self.keypress_height_spin, 'keypress_display_height', 40),
            ]:
                slider.blockSignals(True); spin.blockSignals(True)
                slider.setValue(sv(key, default)); spin.setValue(sv(key, default))
                slider.blockSignals(False); spin.blockSignals(False)

    def load_layer_properties(self):
        if not self.current_layer:
            return
        layer = self.current_layer
        self.name_edit.setText(layer.name)
        if self._is_default_layer(layer):
            x, y, w, h = self._get_default_layer_display_values(layer)
            self.x_spin.setValue(x); self.y_spin.setValue(y)
            self.width_spin.setValue(w); self.height_spin.setValue(h)
            self.follow_combo.setCurrentIndex(0)
            self._load_extra_panel_values(layer.layer_key)
            layer_key_to_filename = {
                'bg': 'bgImage.png',
                'keyboard': 'keyboardImage.png',
                'mouse_click': 'mouseImage.png',
            }
            filename = layer_key_to_filename.get(layer.layer_key)
            if filename and self.character_name:
                character_dir = path_manager.get_character_dir(self.character_name)
                backup_path = os.path.join(character_dir, filename + '.bak')
                self.image_btn.setText("已替换（点击再次替换）" if os.path.exists(backup_path) else "选择图片（替换原图）")
            else:
                self.image_btn.setText("选择图片（替换原图）")
        else:
            self.x_spin.setValue(layer.x); self.y_spin.setValue(layer.y)
            self.width_spin.setValue(layer.width); self.height_spin.setValue(layer.height)
            follow_map = {"none": 0, "keyboard": 1, "mouse": 2}
            self.follow_combo.setCurrentIndex(follow_map.get(layer.follow_type, 0))
            self.image_btn.setText("选择图片")
        self.opacity_spin.setValue(layer.opacity)
        self.visible_check.setChecked(layer.visible)

    def clear_layer_properties(self):
        self.name_edit.setText("未选择图层")
        self.x_spin.setValue(0); self.y_spin.setValue(0)
        self.width_spin.setValue(100); self.height_spin.setValue(100)
        self.follow_combo.setCurrentIndex(0)
        self.opacity_spin.setValue(1.0)
        self.visible_check.setChecked(True)

    def disconnect_property_signals(self):
        try:
            self.x_spin.valueChanged.disconnect(self.on_property_changed)
            self.y_spin.valueChanged.disconnect(self.on_property_changed)
            self.width_spin.valueChanged.disconnect(self.on_property_changed)
            self.height_spin.valueChanged.disconnect(self.on_property_changed)
            self.follow_combo.currentTextChanged.disconnect(self.on_property_changed)
            self.opacity_spin.valueChanged.disconnect(self.on_property_changed)
            self.visible_check.stateChanged.disconnect(self.on_property_changed)
        except TypeError:
            pass

    def connect_property_signals(self):
        self.x_spin.valueChanged.connect(self.on_property_changed)
        self.y_spin.valueChanged.connect(self.on_property_changed)
        self.width_spin.valueChanged.connect(self.on_property_changed)
        self.height_spin.valueChanged.connect(self.on_property_changed)
        self.follow_combo.currentTextChanged.connect(self.on_property_changed)
        self.opacity_spin.valueChanged.connect(self.on_property_changed)
        self.visible_check.stateChanged.connect(self.on_property_changed)

    def on_property_changed(self):
        if not self.current_layer:
            return
        layer = self.current_layer
        is_default = self._is_default_layer(layer)

        if not is_default:
            layer.x = self.x_spin.value()
            layer.y = self.y_spin.value()
            layer.width = self.width_spin.value()
            layer.height = self.height_spin.value()
            follow_map = {0: "none", 1: "keyboard", 2: "mouse"}
            layer.follow_type = follow_map[self.follow_combo.currentIndex()]

        layer.opacity = self.opacity_spin.value()
        layer.visible = self.visible_check.isChecked()

        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

        # 更新列表项文本
        current_item = self.layer_list.item(self.current_index)
        if current_item:
            vis = '可见' if layer.visible else '隐藏'
            expected = f"[默认] {layer.name} ({vis})" if is_default else f"{layer.name} ({vis})"
            if current_item.text() != expected:
                self.layer_list.currentRowChanged.disconnect()
                current_item.setText(expected)
                self.layer_list.currentRowChanged.connect(self.on_layer_selected)

    # ------------------------------------------------------------------
    # 图片选择
    # ------------------------------------------------------------------

    def select_image(self):
        if not self.current_layer:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not file_path:
            return

        if self._is_default_layer(self.current_layer):
            layer_key_to_filename = {
                'bg': 'bgImage.png',
                'keyboard': 'keyboardImage.png',
                'mouse_click': 'mouseImage.png',
            }
            filename = layer_key_to_filename.get(self.current_layer.layer_key)
            if not filename or not self.character_name:
                return
            character_dir = path_manager.get_character_dir(self.character_name)
            target_path = os.path.join(character_dir, filename)
            backup_path = target_path + '.bak'
            try:
                if not os.path.exists(backup_path):
                    shutil.copy2(target_path, backup_path)
                shutil.copy2(file_path, target_path)
                self.image_btn.setText(f"已替换: {os.path.basename(file_path)}")
                # 刷新主窗口对应 label
                label_map = {'bg': 'bg_label', 'keyboard': 'keyboard_label', 'mouse_click': 'mouse_label'}
                attr = label_map.get(self.current_layer.layer_key)
                if attr and self.parent() and hasattr(self.parent(), attr):
                    getattr(self.parent(), attr).setPixmap(QPixmap(target_path))
            except Exception as e:
                QMessageBox.warning(self, "替换失败", f"无法替换图片文件：{e}")
                return
        else:
            self.current_layer.image_path = file_path

        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    # ------------------------------------------------------------------
    # 图层增删移动
    # ------------------------------------------------------------------

    def add_layer(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            layer = CustomLayer(
                name=name, image_path=file_path,
                x=0, y=0, width=100, height=100,
                follow_type="none", opacity=1.0, visible=True,
                z_index=len(self.all_layers)
            )
            self.all_layers.append(layer)
            self._normalize_z_indices()
            self.load_layer_list()
            self.layer_list.setCurrentRow(len(self.all_layers) - 1)
            if self.realtime_preview_check.isChecked():
                self.layers_changed.emit()

    def remove_layer(self):
        if self.current_index < 0 or self._is_default_layer(self.current_layer):
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除图层 '{self.current_layer.name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.all_layers.pop(self.current_index)
            self._normalize_z_indices()
            self.load_layer_list()
            self.current_index = -1
            self.current_layer = None
            self.set_properties_enabled(False)
            if self.realtime_preview_check.isChecked():
                self.layers_changed.emit()

    def on_layer_rows_moved(self, parent, src, end, dest_parent, dest):
        to = dest if dest <= src else dest - 1
        self.all_layers.insert(to, self.all_layers.pop(src))
        self._normalize_z_indices()
        self.layer_list.currentRowChanged.disconnect(self.on_layer_selected)
        self.layer_list.setCurrentRow(to)
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        self.current_index = to
        self.current_layer = self.all_layers[to]
        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    def move_layer_up(self):
        if self.current_index <= 0:
            return
        i = self.current_index
        self.all_layers[i], self.all_layers[i - 1] = self.all_layers[i - 1], self.all_layers[i]
        self._normalize_z_indices()
        self.load_layer_list()
        self.layer_list.setCurrentRow(i - 1)
        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    def move_layer_down(self):
        if self.current_index < 0 or self.current_index >= len(self.all_layers) - 1:
            return
        i = self.current_index
        self.all_layers[i], self.all_layers[i + 1] = self.all_layers[i + 1], self.all_layers[i]
        self._normalize_z_indices()
        self.load_layer_list()
        self.layer_list.setCurrentRow(i + 1)
        if self.realtime_preview_check.isChecked():
            self.layers_changed.emit()

    # ------------------------------------------------------------------
    # 应用 / 关闭 / 未保存检测
    # ------------------------------------------------------------------

    def apply_changes(self):
        """保存所有修改，all_layers 是唯一真相来源"""
        self._normalize_z_indices()

        # 保存自定义图层
        custom_layers = [l for l in self.all_layers if not self._is_default_layer(l)]
        self.layer_manager.layers = [CustomLayer.from_dict(l.to_dict()) for l in custom_layers]
        self.layer_manager.save_layers()

        # 保存默认图层属性和完整图层顺序
        layer_order_data = {}
        layer_order_list = []
        
        # 保存默认图层属性
        for layer in self.all_layers:
            if self._is_default_layer(layer):
                layer_order_data[layer.layer_key] = layer.to_dict()
        
        # 保存完整图层顺序
        for layer in self.all_layers:
            if self._is_default_layer(layer):
                layer_order_list.append({
                    'layer_key': layer.layer_key,
                    'type': 'default'
                })
            else:
                layer_order_list.append({
                    'name': layer.name,
                    'type': 'custom'
                })
        
        # 将图层顺序添加到配置中
        layer_order_data['layer_order'] = layer_order_list

        # 先保存图像调整设置（必须在 save_layer_config 之前）
        # 因为 Settings.save() 会回写初始化时读到的旧 layer_order，
        # 如果顺序颠倒会把新保存的图层顺序冲掉
        if self.settings and self.temp_settings:
            keys_to_save = [
                'window_width', 'window_height',
                'bg_width', 'bg_height',
                'keyboard_x', 'keyboard_y', 'keyboard_width', 'keyboard_height',
                'keyboard_press_offset', 'keyboard_horizontal_travel',
                'mouse_x', 'mouse_y', 'mouse_width', 'mouse_height',
                'max_mouse_offset', 'mouse_sensitivity', 'mouse_return_speed', 'sync_scale_enabled',
                'keypress_display_enabled', 'keypress_display_x', 'keypress_display_y',
                'keypress_display_font_size', 'keypress_display_max_width', 'keypress_display_height',
            ]
            for key in keys_to_save:
                if key in self.temp_settings:
                    self.settings.set(key, self.temp_settings[key])
            self.settings.save()
        
        # 再保存图层顺序配置（会覆盖 settings.save 写入的旧值）
        save_layer_config(self.character_name, layer_order_data)

        # 更新快照（apply 后视为已保存）
        self._saved_snapshot = self._make_snapshot()

        # 通知主程序，携带当前有序图层列表
        self.layers_applied.emit(list(self.all_layers))
        QMessageBox.information(self, "提示", "图层设置已保存！")

    def has_unsaved_changes(self):
        return self._make_snapshot() != self._saved_snapshot

    def closeEvent(self, event):
        # 关闭时确保取消按键预览
        self.keypress_preview_requested.emit(False)
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "未保存的修改",
                "您有未保存的修改，是否要保存？\n\n"
                "是 - 保存并关闭\n否 - 不保存直接关闭\n取消 - 返回继续编辑",
                QMessageBox.StandardButton.Yes |
                QMessageBox.StandardButton.No |
                QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.apply_changes()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                # 恢复主窗口到已保存状态
                self.layers_applied.emit(None)
                event.accept()
            else:
                event.ignore()
                return
        else:
            event.accept()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # 快捷操作
    # ------------------------------------------------------------------

    def reset_position(self):
        if not self.current_layer or self._is_default_layer(self.current_layer):
            return
        self.disconnect_property_signals()
        self.x_spin.setValue(0); self.y_spin.setValue(0)
        self.connect_property_signals()
        self.on_property_changed()

    def reset_size(self):
        if not self.current_layer or self._is_default_layer(self.current_layer):
            return
        self.disconnect_property_signals()
        self.width_spin.setValue(100); self.height_spin.setValue(100)
        self.connect_property_signals()
        self.on_property_changed()

    def set_semi_transparent(self):
        if not self.current_layer:
            return
        self.disconnect_property_signals()
        self.opacity_spin.setValue(0.5)
        self.connect_property_signals()
        self.on_property_changed()

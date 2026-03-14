"""
测试按键显示功能
"""
import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget
from PyQt6.QtCore import Qt, QTimer

def test_keypress_display():
    """测试按键显示标签的创建和样式"""
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = QWidget()
    window.setWindowTitle("按键显示测试")
    window.resize(400, 300)
    
    # 创建按键显示标签
    keypress_label = QLabel(window)
    keypress_label.setStyleSheet(
        "color: white; "
        "background-color: rgba(0, 0, 0, 150); "
        "padding: 5px; "
        "border-radius: 5px; "
        "font-size: 16px; "
        "font-weight: bold;"
    )
    keypress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    keypress_label.setGeometry(10, 10, 100, 40)
    
    # 测试不同的按键显示
    test_keys = ['A', 'Space', 'Enter', 'Ctrl', '↑', 'F1']
    current_key_index = [0]
    
    def show_next_key():
        if current_key_index[0] < len(test_keys):
            key = test_keys[current_key_index[0]]
            keypress_label.setText(key)
            keypress_label.adjustSize()
            keypress_label.show()
            current_key_index[0] += 1
            print(f"显示按键: {key}")
        else:
            print("测试完成！")
            QTimer.singleShot(1000, app.quit)
    
    # 每秒显示一个按键
    timer = QTimer()
    timer.timeout.connect(show_next_key)
    timer.start(1000)
    
    window.show()
    show_next_key()  # 立即显示第一个按键
    
    sys.exit(app.exec())

if __name__ == '__main__':
    print("开始测试按键显示功能...")
    print("将依次显示不同的按键")
    test_keypress_display()

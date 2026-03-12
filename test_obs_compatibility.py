#!/usr/bin/env python3
"""
测试OBS兼容性的简单脚本
运行此脚本来验证窗口是否可以被OBS识别
"""

import sys
from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

def test_window_visibility():
    """测试窗口是否可以被外部程序识别"""
    app = QApplication(sys.argv)
    
    # 创建测试窗口，使用与main.py相同的设置
    window = QLabel("OBS测试窗口")
    
    # 使用修复后的窗口标志
    flags = Qt.WindowType.FramelessWindowHint
    window.setWindowFlags(flags)
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    window.setWindowTitle("ASoul Little Bun - OBS Test")
    window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
    
    # 设置窗口大小和位置
    window.resize(300, 200)
    window.move(100, 100)
    
    # 设置一些可见内容
    window.setStyleSheet("""
        QLabel {
            background-color: rgba(255, 0, 0, 128);
            color: white;
            font-size: 16px;
            padding: 20px;
            border: 2px solid white;
        }
    """)
    
    window.show()
    
    print("测试窗口已启动！")
    print("请检查OBS是否可以识别到名为 'ASoul Little Bun - OBS Test' 的窗口")
    print("按 Ctrl+C 退出测试")
    
    try:
        app.exec()
    except KeyboardInterrupt:
        print("\n测试结束")

if __name__ == "__main__":
    test_window_visibility()
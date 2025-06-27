import sys
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QTabWidget, QGridLayout, QMessageBox,
                            QGraphicsScene, QGraphicsView, QGraphicsRectItem, QFrame, QDialog,
                            QTextEdit, QDialogButtonBox)
from PyQt5.QtCore import QTimer, Qt, QDateTime, QRectF, QTime
from PyQt5.QtGui import QFont, QBrush, QColor, QPen, QLinearGradient, QGradient

class PomodoroTimer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("番茄工作法计时器")
        self.setGeometry(300, 300, 800, 600)
        
        # 设置程序目录和数据文件路径
        # 判断是否是PyInstaller打包的应用
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # 如果是打包后的应用，使用可执行文件所在目录作为应用目录
            self.app_dir = os.path.dirname(sys.executable)
        else:
            # 如果是开发环境，使用脚本所在目录
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.history_file = os.path.join(self.app_dir, "pomodoro_history.json")
        self.state_file = os.path.join(self.app_dir, "pomodoro_state.json")
        
        # 设置应用程序样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #505050;
                min-width: 80px;
                padding: 8px 16px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #e74c3c;
                font-weight: bold;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QLabel {
                color: #333333;
            }
            QGraphicsView {
                background-color: #ffffff;
                border: 1px solid #dddddd;
                border-radius: 5px;
            }
            QDialog {
                background-color: #ffffff;
            }
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                color: #333333;
                font-size: 14px;
            }
        """)
        
        # 初始化变量
        self.work_time = 25 * 60  # 25分钟工作时间（秒）
        self.break_time = 10 * 60  # 10分钟休息时间（秒）
        self.time_left = self.work_time
        self.is_working = True
        self.is_running = False
        self.is_idle_break = False
        
        self.today_work_time = 0
        self.today_break_time = 0
        self.today_idle_time = 0
        
        self.start_time: Optional[datetime] = None
        self.current_session_start: Optional[datetime] = None
        self.idle_break_start: Optional[datetime] = None
        
        # 创建UI
        self.init_ui()
        
        # 初始化计时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        # 加载历史数据
        self.history_data = self.load_history_data()
        self.update_history_display()
        
        # 添加自动保存计时器，每60秒保存一次数据
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.save_history_data)
        self.autosave_timer.start(60000)  # 每60秒保存一次
        
        # 恢复之前的状态（如果有）
        self.load_state()
        
    def init_ui(self):
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 创建选项卡
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 计时器选项卡
        timer_tab = QWidget()
        timer_layout = QVBoxLayout(timer_tab)
        timer_layout.setContentsMargins(20, 20, 20, 20)
        timer_layout.setSpacing(20)
        
        # 添加计时器显示框
        timer_frame = QFrame()
        timer_frame.setFrameShape(QFrame.StyledPanel)
        timer_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        timer_frame_layout = QVBoxLayout(timer_frame)
        
        # 添加计时器显示
        self.time_display = QLabel("25:00")
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setFont(QFont("Arial", 72, QFont.Bold))
        self.time_display.setStyleSheet("""
            color: #e74c3c;
            margin: 10px;
        """)
        timer_frame_layout.addWidget(self.time_display)
        
        # 添加状态显示
        self.status_label = QLabel("准备开始工作")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 16))
        self.status_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        timer_frame_layout.addWidget(self.status_label)
        
        timer_layout.addWidget(timer_frame)
        
        # 添加今日统计
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.StyledPanel)
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 10px;
            }
            QLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
        stats_layout = QGridLayout(stats_frame)
        stats_layout.setSpacing(10)
        
        stats_layout.addWidget(QLabel("今日工作时间:"), 0, 0)
        self.work_time_label = QLabel("00:00:00")
        self.work_time_label.setStyleSheet("color: #3498db; font-weight: bold;")
        stats_layout.addWidget(self.work_time_label, 0, 1)
        
        stats_layout.addWidget(QLabel("今日休息时间:"), 1, 0)
        self.break_time_label = QLabel("00:00:00")
        self.break_time_label.setStyleSheet("color: #2ecc71; font-weight: bold;")
        stats_layout.addWidget(self.break_time_label, 1, 1)
        
        stats_layout.addWidget(QLabel("今日空闲休息时间:"), 2, 0)
        self.idle_time_label = QLabel("00:00:00")
        self.idle_time_label.setStyleSheet("color: #f39c12; font-weight: bold;")
        stats_layout.addWidget(self.idle_time_label, 2, 1)
        
        timer_layout.addWidget(stats_frame)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.start_button = QPushButton("开始")
        self.start_button.setMinimumHeight(50)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.start_button.clicked.connect(self.toggle_timer)
        button_layout.addWidget(self.start_button)
        
        self.idle_break_button = QPushButton("空闲休息")
        self.idle_break_button.setMinimumHeight(50)
        self.idle_break_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #d35400;
            }
        """)
        self.idle_break_button.clicked.connect(self.toggle_idle_break)
        button_layout.addWidget(self.idle_break_button)
        
        self.reset_button = QPushButton("重置")
        self.reset_button.setMinimumHeight(50)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #636e72;
            }
        """)
        self.reset_button.clicked.connect(self.reset_timer)
        button_layout.addWidget(self.reset_button)
        
        timer_layout.addLayout(button_layout)
        
        # 添加查看报告按钮
        report_button = QPushButton("查看学习报告")
        report_button.setMinimumHeight(40)
        report_button.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                font-size: 14px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        report_button.clicked.connect(self.show_report)
        timer_layout.addWidget(report_button)
        
        # 历史记录选项卡
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        history_layout.setContentsMargins(20, 20, 20, 20)
        
        history_title = QLabel("每日时间统计")
        history_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_title.setFont(QFont("Arial", 16, QFont.Bold))
        history_title.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        history_layout.addWidget(history_title)
        
        # 创建自定义图表视图
        self.chart_view = QGraphicsView()
        self.chart_view.setMinimumHeight(400)
        self.chart_view.setStyleSheet("""
            QGraphicsView {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
            }
        """)
        self.chart_scene = QGraphicsScene()
        self.chart_view.setScene(self.chart_scene)
        history_layout.addWidget(self.chart_view)
        
        # 添加选项卡到主选项卡窗口
        tabs.addTab(timer_tab, "计时器")
        tabs.addTab(history_tab, "历史记录")
        
    def toggle_timer(self):
        if not self.is_running:
            # 开始计时
            self.is_running = True
            self.start_button.setText("暂停")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
            """)
            self.idle_break_button.setEnabled(True)
            
            if self.current_session_start is None:
                self.current_session_start = datetime.now()
                
            if self.start_time is None:
                # 如果是第一次启动，记录开始时间
                self.start_time = datetime.now()
                
            self.timer.start(1000)  # 每秒更新一次
        else:
            # 暂停计时
            self.is_running = False
            self.start_button.setText("继续")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
            self.timer.stop()
            
            # 暂停时保存数据
            self.save_history_data()
            
    def toggle_idle_break(self):
        if not self.is_idle_break:
            # 开始空闲休息
            self.is_idle_break = True
            self.idle_break_button.setText("结束空闲休息")
            
            # 如果计时器正在运行，先暂停
            was_running = self.is_running
            if self.is_running:
                # 暂停计时器但不调用toggle_timer以避免状态混淆
                self.is_running = False
                self.timer.stop()
                self.start_button.setText("继续")
                self.start_button.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        font-size: 16px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                """)
                
            # 记录当前时间作为空闲休息开始时间
            self.idle_break_start = datetime.now()
            self.current_idle_time = 0
            
            # 更新状态显示
            self.status_label.setText("空闲休息中...")
            self.status_label.setStyleSheet("color: #f39c12; margin-bottom: 10px; font-weight: bold;")
            
            # 禁用开始按钮
            self.start_button.setEnabled(False)
            
            # 创建一个新的计时器用于实时更新空闲休息时间
            if hasattr(self, 'idle_timer') and self.idle_timer.isActive():
                self.idle_timer.stop()
            self.idle_timer = QTimer(self)
            self.idle_timer.timeout.connect(self.update_idle_time)
            self.idle_timer.start(1000)  # 每秒更新一次
            
            # 更新显示为空闲休息模式
            self.time_display.setText("00:00")
            self.time_display.setStyleSheet("color: #f39c12; margin: 10px;")
        else:
            # 结束空闲休息
            self.is_idle_break = False
            self.idle_break_button.setText("空闲休息")
            
            # 停止空闲计时器
            if hasattr(self, 'idle_timer') and self.idle_timer.isActive():
                self.idle_timer.stop()
            
            # 计算空闲休息时间
            if self.idle_break_start is not None:
                idle_duration = (datetime.now() - self.idle_break_start).total_seconds()
                self.today_idle_time += int(idle_duration)
            
            # 空闲休息结束后，始终回到工作状态
            self.is_working = True
            self.time_left = self.work_time
            
            # 更新显示
            self.update_time_displays()
            
            # 更新状态显示
            self.status_label.setText("准备工作")
            self.status_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
            
            # 恢复开始按钮
            self.start_button.setEnabled(True)
            
            # 恢复计时器显示的颜色为工作模式颜色
            self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
            
            # 更新计时器显示
            self.update_time_display()
            
            # 空闲休息结束时保存数据
            self.save_history_data()
            
    def update_idle_time(self):
        # 计算当前已经空闲的时间（秒）
        if self.idle_break_start is not None:
            current_duration = (datetime.now() - self.idle_break_start).total_seconds()
            
            # 更新显示
            minutes = int(current_duration) // 60
            seconds = int(current_duration) % 60
            self.time_display.setText(f"{minutes:02d}:{seconds:02d}")
            
            # 同时更新今日空闲时间显示（仅用于实时预览）
            preview_idle_time = self.today_idle_time + int(current_duration)
            self.idle_time_label.setText(self.format_time(preview_idle_time))
        
    def update_timer(self):
        if self.time_left > 0:
            # 确保不在空闲休息模式下
            if not self.is_idle_break:
                self.time_left -= 1
                
                # 更新当前会话时间
                if self.is_working:
                    self.today_work_time += 1
                else:
                    self.today_break_time += 1
                    
                # 更新显示
                self.update_time_displays()
        else:
            # 时间到，切换模式
            self.timer.stop()
            
            if self.is_working:
                # 工作时间结束，切换到休息时间
                self.is_working = False
                self.time_left = self.break_time
                self.status_label.setText("休息时间")
                self.status_label.setStyleSheet("color: #2ecc71; margin-bottom: 10px; font-weight: bold;")
                self.time_display.setStyleSheet("color: #2ecc71; margin: 10px;")
                QMessageBox.information(self, "提示", "工作时间结束，请休息一下！")
            else:
                # 休息时间结束，切换到工作时间
                self.is_working = True
                self.time_left = self.work_time
                self.status_label.setText("工作时间")
                self.status_label.setStyleSheet("color: #e74c3c; margin-bottom: 10px; font-weight: bold;")
                self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
                QMessageBox.information(self, "提示", "休息时间结束，继续工作！")
                
            # 更新显示
            self.update_time_display()
            
            # 保存历史数据
            self.save_history_data()
            
            # 重新启动计时器
            self.is_running = False
            self.start_button.setText("开始")
            self.start_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
            """)
    
    def reset_timer(self):
        # 停止计时器
        self.timer.stop()
        
        # 重置变量
        self.is_working = True
        self.is_running = False
        self.time_left = self.work_time
        
        # 更新UI
        self.start_button.setText("开始")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.status_label.setText("准备工作")
        self.status_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
        self.update_time_display()
        
        # 重置时保存数据
        self.save_history_data()
    
    def update_time_display(self):
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.time_display.setText(f"{minutes:02d}:{seconds:02d}")
        
    def update_time_displays(self):
        # 更新计时器显示
        self.update_time_display()
        
        # 更新今日统计显示
        self.work_time_label.setText(self.format_time(self.today_work_time))
        self.break_time_label.setText(self.format_time(self.today_break_time))
        self.idle_time_label.setText(self.format_time(self.today_idle_time))
        
    def format_time(self, seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def load_history_data(self):
        # 尝试从文件加载历史数据
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    
                # 检查今天的数据是否存在
                today = datetime.now().strftime("%Y-%m-%d")
                if today in data:
                    # 加载今天的数据
                    self.today_work_time = data[today]["work_time"]
                    self.today_break_time = data[today]["break_time"]
                    self.today_idle_time = data[today]["idle_time"]
                    
                return data
            except Exception as e:
                print(f"加载历史数据失败: {e}")
                return {}
        else:
            return {}
    
    def save_history_data(self):
        # 保存历史数据到文件
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 更新或创建今天的数据
        self.history_data[today] = {
            "work_time": self.today_work_time,
            "break_time": self.today_break_time,
            "idle_time": self.today_idle_time
        }
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            
            with open(self.history_file, "w") as f:
                json.dump(self.history_data, f)
                
            # 更新历史记录显示
            self.update_history_display()
        except Exception as e:
            print(f"保存历史数据失败: {e}")
            QMessageBox.warning(self, "保存失败", f"无法保存数据到 {self.history_file}。\n错误信息: {e}")
    
    def update_history_display(self):
        # 更新历史记录图表
        if not self.history_data:
            return
            
        # 清除现有图表
        self.chart_scene.clear()
        
        # 准备数据
        dates = []
        work_times = []
        break_times = []
        idle_times = []
        total_times = []
        
        # 获取最近7天的数据（如果有）
        sorted_dates = sorted(self.history_data.keys())
        recent_dates = sorted_dates[-7:] if len(sorted_dates) > 7 else sorted_dates
        
        for date in recent_dates:
            dates.append(date)
            work_time = self.history_data[date]["work_time"] / 3600  # 转换为小时
            break_time = self.history_data[date]["break_time"] / 3600
            idle_time = self.history_data[date]["idle_time"] / 3600
            total_time = work_time + break_time + idle_time
            
            work_times.append(work_time)
            break_times.append(break_time)
            idle_times.append(idle_time)
            total_times.append(total_time)
        
        # 设置图表尺寸
        chart_width = 700
        chart_height = 400
        self.chart_scene.setSceneRect(0, 0, chart_width, chart_height)
        
        # 设置背景
        background = QGraphicsRectItem(0, 0, chart_width, chart_height)
        background.setBrush(QBrush(QColor("#ffffff")))
        self.chart_scene.addItem(background)
        
        # 设置横向条形图参数
        bar_height = 30
        bar_spacing = 15
        margin_left = 100
        margin_right = 200
        margin_top = 50
        margin_bottom = 50
        
        # 添加标题
        title = self.chart_scene.addText("每日时间分布")
        title.setDefaultTextColor(QColor("#2c3e50"))
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setPos((chart_width - title.boundingRect().width()) / 2, 10)
        
        # 绘制横向条形图
        for i, date in enumerate(dates):
            y_pos = margin_top + i * (bar_height + bar_spacing)
            
            # 添加日期标签
            date_label = self.chart_scene.addText(date)
            date_label.setDefaultTextColor(QColor("#2c3e50"))
            date_label.setPos(10, y_pos + (bar_height - date_label.boundingRect().height()) / 2)
            
            # 计算总宽度
            usable_width = chart_width - margin_left - margin_right
            
            # 如果总时间为0，显示空条
            if total_times[i] == 0:
                empty_bar = QGraphicsRectItem(margin_left, y_pos, usable_width, bar_height)
                empty_bar.setBrush(QBrush(QColor("#f0f0f0")))
                empty_bar.setPen(QPen(QColor("#e0e0e0")))
                self.chart_scene.addItem(empty_bar)
                
                # 添加"无数据"文本
                no_data = self.chart_scene.addText("无数据")
                no_data.setDefaultTextColor(QColor("#7f8c8d"))
                no_data.setPos(margin_left + 10, y_pos + (bar_height - no_data.boundingRect().height()) / 2)
                continue
            
            # 绘制工作时间条
            work_width = (work_times[i] / total_times[i]) * usable_width
            if work_width > 0:
                work_bar = QGraphicsRectItem(margin_left, y_pos, work_width, bar_height)
                gradient = QLinearGradient(margin_left, 0, margin_left + work_width, 0)
                gradient.setColorAt(0, QColor(52, 152, 219))
                gradient.setColorAt(1, QColor(41, 128, 185))
                work_bar.setBrush(QBrush(gradient))
                work_bar.setPen(QPen(Qt.PenStyle.NoPen))
                self.chart_scene.addItem(work_bar)
            
            # 绘制休息时间条
            break_width = (break_times[i] / total_times[i]) * usable_width
            if break_width > 0:
                break_bar = QGraphicsRectItem(margin_left + work_width, y_pos, break_width, bar_height)
                gradient = QLinearGradient(margin_left + work_width, 0, margin_left + work_width + break_width, 0)
                gradient.setColorAt(0, QColor(46, 204, 113))
                gradient.setColorAt(1, QColor(39, 174, 96))
                break_bar.setBrush(QBrush(gradient))
                break_bar.setPen(QPen(Qt.PenStyle.NoPen))
                self.chart_scene.addItem(break_bar)
            
            # 绘制空闲休息时间条
            idle_width = (idle_times[i] / total_times[i]) * usable_width
            if idle_width > 0:
                idle_bar = QGraphicsRectItem(margin_left + work_width + break_width, y_pos, idle_width, bar_height)
                gradient = QLinearGradient(margin_left + work_width + break_width, 0, 
                                          margin_left + work_width + break_width + idle_width, 0)
                gradient.setColorAt(0, QColor(243, 156, 18))
                gradient.setColorAt(1, QColor(211, 84, 0))
                idle_bar.setBrush(QBrush(gradient))
                idle_bar.setPen(QPen(Qt.PenStyle.NoPen))
                self.chart_scene.addItem(idle_bar)
            
            # 添加时间数据标签
            data_text = f"工作: {self.format_time_short(work_times[i])} | 休息: {self.format_time_short(break_times[i])} | 空闲: {self.format_time_short(idle_times[i])}"
            data_label = self.chart_scene.addText(data_text)
            data_label.setDefaultTextColor(QColor("#2c3e50"))
            data_label.setPos(margin_left + usable_width + 10, y_pos + (bar_height - data_label.boundingRect().height()) / 2)
        
        # 添加图例
        legend_x = margin_left
        legend_y = margin_top + len(dates) * (bar_height + bar_spacing) + 20
        
        # 绘制图例背景
        legend_bg = QGraphicsRectItem(legend_x - 10, legend_y - 10, 350, 40)
        legend_bg.setBrush(QBrush(QColor(255, 255, 255, 200)))
        legend_bg.setPen(QPen(QColor("#e0e0e0")))
        self.chart_scene.addItem(legend_bg)
        
        # 工作时间图例
        work_legend = QGraphicsRectItem(legend_x, legend_y, 15, 15)
        gradient = QLinearGradient(0, legend_y, 15, legend_y)
        gradient.setColorAt(0, QColor(52, 152, 219))
        gradient.setColorAt(1, QColor(41, 128, 185))
        work_legend.setBrush(QBrush(gradient))
        work_legend.setPen(QPen(Qt.PenStyle.NoPen))
        self.chart_scene.addItem(work_legend)
        work_text = self.chart_scene.addText("工作时间")
        work_text.setDefaultTextColor(QColor("#2c3e50"))
        work_text.setPos(legend_x + 20, legend_y - 5)
        
        # 休息时间图例
        break_legend = QGraphicsRectItem(legend_x + 120, legend_y, 15, 15)
        gradient = QLinearGradient(0, legend_y, 15, legend_y)
        gradient.setColorAt(0, QColor(46, 204, 113))
        gradient.setColorAt(1, QColor(39, 174, 96))
        break_legend.setBrush(QBrush(gradient))
        break_legend.setPen(QPen(Qt.PenStyle.NoPen))
        self.chart_scene.addItem(break_legend)
        break_text = self.chart_scene.addText("休息时间")
        break_text.setDefaultTextColor(QColor("#2c3e50"))
        break_text.setPos(legend_x + 140, legend_y - 5)
        
        # 空闲休息时间图例
        idle_legend = QGraphicsRectItem(legend_x + 240, legend_y, 15, 15)
        gradient = QLinearGradient(0, legend_y, 15, legend_y)
        gradient.setColorAt(0, QColor(243, 156, 18))
        gradient.setColorAt(1, QColor(211, 84, 0))
        idle_legend.setBrush(QBrush(gradient))
        idle_legend.setPen(QPen(Qt.PenStyle.NoPen))
        self.chart_scene.addItem(idle_legend)
        idle_text = self.chart_scene.addText("空闲休息时间")
        idle_text.setDefaultTextColor(QColor("#2c3e50"))
        idle_text.setPos(legend_x + 260, legend_y - 5)
    
    def format_time_short(self, hours):
        """将小时数格式化为小时和分钟"""
        h = int(hours)
        m = int((hours - h) * 60)
        if h > 0:
            return f"{h}h {m}m"
        else:
            return f"{m}m"
    
    def generate_daily_report(self):
        # 获取当前日期和昨天的日期
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        today_str = today.strftime("%Y-%m-%d")
        yesterday_str = yesterday.strftime("%Y-%m-%d")
        
        # 创建报告对话框
        report_dialog = QDialog(self)
        report_dialog.setWindowTitle("学习报告")
        report_dialog.setMinimumSize(500, 400)
        
        # 创建报告内容
        report_text = QTextEdit(report_dialog)
        report_text.setReadOnly(True)
        
        # 创建对话框按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, report_dialog)
        buttons.accepted.connect(report_dialog.accept)
        
        # 创建布局
        layout = QVBoxLayout(report_dialog)
        layout.addWidget(report_text)
        layout.addWidget(buttons)
        
        # 开始构建报告内容
        report_content = f"<h2 style='color: #3498db; text-align: center;'>📊 {today_str} 学习报告</h2>"
        report_content += "<hr>"
        
        # 检查昨天的数据是否存在
        if yesterday_str in self.history_data and today_str in self.history_data:
            # 获取今天和昨天的数据
            today_data = self.history_data[today_str]
            yesterday_data = self.history_data[yesterday_str]
            
            # 如果昨天数据为null或0，说明可能有其他事情，不进行比较
            if yesterday_data["work_time"] == 0:
                report_content += f"<p>昨天没有记录到学习数据，可能有其他事情。</p>"
                today_work_hours = today_data["work_time"] / 3600
                report_content += f"<p>今天已经学习了 <b style='color: #3498db;'>{self.format_time(today_data['work_time'])}</b>。</p>"
                report_content += "<p>继续保持！💪</p>"
            else:
                # 计算今天和昨天的工作时间（小时）
                today_work_hours = today_data["work_time"] / 3600
                yesterday_work_hours = yesterday_data["work_time"] / 3600
                
                # 计算差异
                diff_hours = today_work_hours - yesterday_work_hours
                diff_percentage = (diff_hours / yesterday_work_hours) * 100 if yesterday_work_hours > 0 else 0
                
                # 添加今天的工作时间信息
                report_content += f"<p><b>今天工作时间:</b> <span style='color: #3498db;'>{self.format_time(today_data['work_time'])}</span></p>"
                report_content += f"<p><b>昨天工作时间:</b> <span style='color: #7f8c8d;'>{self.format_time(yesterday_data['work_time'])}</span></p>"
                
                # 根据对比结果给出鼓励或提醒
                if diff_hours >= 0:
                    # 做得更好
                    report_content += f"<p style='background-color: #e8f8f5; padding: 10px; border-radius: 5px;'>🎉 <b>做得好！</b> 今天比昨天多学习了 <b style='color: #27ae60;'>{self.format_time(int(diff_hours * 3600))}</b> ({diff_percentage:.1f}%)。</p>"
                    
                    # 根据工作时间的长短给出不同的鼓励
                    if today_work_hours > 6:
                        report_content += "<p>你今天的学习时间非常充实！继续保持这样的热情，相信你一定能够达成你的目标！💪</p>"
                    elif today_work_hours > 3:
                        report_content += "<p>你的学习状态很好，请继续保持！坚持就是胜利！😊</p>"
                    else:
                        report_content += "<p>虽然时间不多，但每一分钟的进步都很重要！明天继续加油！🌟</p>"
                else:
                    # 做得不太好
                    abs_diff_hours = abs(diff_hours)
                    report_content += f"<p style='background-color: #fef5e7; padding: 10px; border-radius: 5px;'>⚠️ <b>提醒：</b> 今天比昨天少学习了 <b style='color: #e74c3c;'>{self.format_time(int(abs_diff_hours * 3600))}</b> ({abs(diff_percentage):.1f}%)。</p>"
                    
                    # 给出建议
                    report_content += "<p>没关系，每个人都有状态起伏的时候。明天试着：</p>"
                    report_content += "<ul>"
                    report_content += "<li>设定一个明确的学习目标</li>"
                    report_content += "<li>避免学习过程中的干扰</li>"
                    report_content += "<li>适当休息，保持精力充沛</li>"
                    report_content += "</ul>"
                    report_content += "<p>相信明天的你会做得更好！加油！🔥</p>"
        else:
            # 如果昨天或今天的数据不存在
            if today_str in self.history_data:
                today_data = self.history_data[today_str]
                report_content += f"<p>今天已经学习了 <b style='color: #3498db;'>{self.format_time(today_data['work_time'])}</b>。</p>"
                report_content += "<p>继续保持！💪</p>"
            else:
                report_content += "<p>今天还没有开始学习记录。现在开始专注一会儿吧！⏰</p>"
            
            if yesterday_str not in self.history_data:
                report_content += "<p>昨天没有学习记录，所以无法进行对比。</p>"
        
        # 添加一些额外的激励语
        motivational_quotes = [
            "坚持不一定会成功，但放弃一定会失败。",
            "每一个成功者都有一个开始。勇于开始，才能找到成功的路。",
            "学习是一种习惯，也是一种享受。",
            "努力的意义，不是一定会成功，而是你可以问心无愧。",
            "成功不是将来才有的，而是从决定去做的那一刻起，持续累积而成。"
        ]
        import random
        report_content += f"<p style='text-align: center; color: #3498db; margin-top: 20px;'><i>\"{random.choice(motivational_quotes)}\"</i></p>"
        
        # 设置报告内容
        report_text.setHtml(report_content)
        
        # 显示对话框
        report_dialog.exec_()
    
    def show_report(self):
        # 手动显示学习报告前先保存当前数据
        self.save_history_data()
        self.generate_daily_report()
    
    def save_state(self):
        # 保存当前状态，以便下次启动时恢复
        state: Dict[str, Any] = {
            "is_working": self.is_working,
            "is_running": self.is_running,
            "is_idle_break": self.is_idle_break,
            "time_left": self.time_left,
            "timestamp": datetime.now().timestamp(),
            "idle_break_timestamp": None
        }
        
        # 如果在空闲休息状态且有开始时间，则保存时间戳
        if self.is_idle_break and self.idle_break_start is not None:
            state["idle_break_timestamp"] = self.idle_break_start.timestamp()
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"保存状态失败: {e}")
            QMessageBox.warning(self, "保存失败", f"无法保存状态到 {self.state_file}。\n错误信息: {e}")
    
    def load_state(self):
        # 加载上次保存的状态
        if not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
                
            # 获取最后保存状态的时间戳
            last_timestamp = state.get("timestamp")
            if not last_timestamp:
                return
                
            # 计算距离上次保存经过的时间（秒）
            elapsed_seconds = int(datetime.now().timestamp() - last_timestamp)
            
            # 恢复工作/休息模式
            self.is_working = state.get("is_working", True)
            
            # 创建状态恢复信息
            status_info = ""
            
            # 恢复空闲休息状态
            if state.get("is_idle_break", False):
                # 恢复空闲休息状态
                idle_break_timestamp = state.get("idle_break_timestamp")
                if idle_break_timestamp:
                    self.idle_break_start = datetime.fromtimestamp(idle_break_timestamp)
                    
                    # 计算已经空闲的时间（分钟）
                    idle_minutes = int((datetime.now() - self.idle_break_start).total_seconds() // 60)
                    
                    # 如果空闲休息时间超过30分钟，假设用户已经完成休息，直接回到工作状态
                    if idle_minutes > 30:
                        # 累加空闲时间到今日统计
                        if self.idle_break_start is not None:
                            idle_duration = (datetime.now() - self.idle_break_start).total_seconds()
                            self.today_idle_time += int(idle_duration)
                        
                        # 设置为工作状态
                        self.is_working = True
                        self.time_left = self.work_time
                        self.status_label.setText("准备工作")
                        self.status_label.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
                        self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
                        self.update_time_display()
                        
                        status_info = f"检测到上次空闲休息已经{idle_minutes}分钟，已重置为工作状态。"
                    else:
                        status_info = f"已恢复空闲休息状态，已经休息了{idle_minutes}分钟。"
                        # 立即启动空闲休息模式
                        self.toggle_idle_break()  # 启动空闲休息
                    
            elif state.get("is_running", False):
                # 恢复计时器状态
                original_time_left = state.get("time_left", self.work_time)
                self.time_left = max(0, original_time_left - elapsed_seconds)
                
                # 如果还有剩余时间，则自动启动计时器
                if self.time_left > 0:
                    minutes_passed = (original_time_left - self.time_left) // 60
                    if self.is_working:
                        status_info = f"已恢复工作计时，已经工作了{minutes_passed}分钟。"
                    else:
                        status_info = f"已恢复休息计时，已经休息了{minutes_passed}分钟。"
                    
                    self.toggle_timer()  # 启动计时器
                else:
                    # 如果时间已经用完，则切换模式并重置
                    if self.is_working:
                        self.is_working = False
                        self.time_left = self.break_time
                        self.status_label.setText("休息时间")
                        self.status_label.setStyleSheet("color: #2ecc71; margin-bottom: 10px; font-weight: bold;")
                        self.time_display.setStyleSheet("color: #2ecc71; margin: 10px;")
                        status_info = "工作时间已结束，已切换到休息时间。"
                    else:
                        self.is_working = True
                        self.time_left = self.work_time
                        self.status_label.setText("工作时间")
                        self.status_label.setStyleSheet("color: #e74c3c; margin-bottom: 10px; font-weight: bold;")
                        self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
                        status_info = "休息时间已结束，已切换到工作时间。"
                    
                    self.update_time_display()
            else:
                # 没有在运行，但更新UI以匹配正确的模式
                if self.is_working:
                    self.time_left = state.get("time_left", self.work_time)
                    self.status_label.setText("准备工作")
                    self.time_display.setStyleSheet("color: #e74c3c; margin: 10px;")
                else:
                    self.time_left = state.get("time_left", self.break_time)
                    self.status_label.setText("准备休息")
                    self.time_display.setStyleSheet("color: #2ecc71; margin: 10px;")
                
                self.update_time_display()
                
            # 在加载状态后显示一个通知
            if status_info:
                QMessageBox.information(self, "状态恢复", status_info)
            
        except Exception as e:
            print(f"加载状态失败: {e}")
            # 加载失败时删除可能损坏的状态文件
            try:
                os.remove(self.state_file)
            except:
                pass
    
    def closeEvent(self, event):
        # 停止计时器
        if hasattr(self, 'idle_timer') and self.idle_timer.isActive():
            self.idle_timer.stop()
            
        # 停止自动保存计时器
        if hasattr(self, 'autosave_timer') and self.autosave_timer.isActive():
            self.autosave_timer.stop()
            
        # 保存当前状态
        self.save_state()
            
        # 应用关闭时保存数据
        self.save_history_data()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PomodoroTimer()
    window.show()
    sys.exit(app.exec_()) 
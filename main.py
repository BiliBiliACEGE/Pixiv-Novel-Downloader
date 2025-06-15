import sys
import re
import json
import logging
import traceback
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, 
                            QLineEdit, QPushButton, QProgressBar, QMessageBox, QDialog,
                            QHBoxLayout, QFileDialog, QComboBox, QTextEdit, QTabWidget, 
                            QListWidget, QListWidgetItem, QFrame, QSizePolicy, QTabBar,
                            QStackedWidget, QCheckBox)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QIcon, QColor
import requests
import os
from datetime import datetime

# 设置日志记录
def setup_logger():
    # 创建logs目录
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建带时间戳的日志文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = os.path.join(log_dir, f"pixiv_novel_downloader_{timestamp}.log")
    
    # 配置日志
    logging.basicConfig(
        filename=log_filename,
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8"
    )
    
    # 添加控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)
    
    logging.info("=" * 80)
    logging.info("Pixiv Novel Downloader 启动")
    logging.info("=" * 80)

class Translator:
    def __init__(self, language="zh_cn"):
        self.language = language
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        try:
            lang_file = os.path.join("locales", f"{self.language}.json")
            if os.path.exists(lang_file):
                with open(lang_file, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                logging.info(f"加载语言文件: {lang_file}")
            else:
                logging.warning(f"语言文件不存在: {lang_file}")
                # 尝试加载默认语言
                default_file = os.path.join("locales", "zh_cn.json")
                if os.path.exists(default_file):
                    with open(default_file, "r", encoding="utf-8") as f:
                        self.translations = json.load(f)
                    logging.info(f"加载默认语言文件: {default_file}")
                else:
                    logging.error("默认语言文件不存在")
        except Exception as e:
            logging.error(f"加载语言文件失败: {str(e)}", exc_info=True)
    
    def translate(self, key, **kwargs):
        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text

class VerticalTabButton(QPushButton):
    """自定义垂直选项卡按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(90, 90)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                border: none;
                border-radius: 10px;
                font-weight: 500;
                color: #495057;
                padding: 0;
                margin: 5px 0;
            }
            QPushButton:checked {
                background-color: #ffffff;
                border-right: 4px solid #4CAF50;
                color: #212529;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dee2e6;
                box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
            }
        """)
        self.setFont(QFont("Arial", 10))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

class PixivNovelDownloader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("PixivNovelDownloader", "PixivNovelDownloader")
        self.translator = Translator(self.settings.value("language", "zh_cn", type=str))
        self._ = self.translator.translate
        
        self.setWindowTitle(self._("app_title"))
        self.setMinimumSize(850, 650)
        
        # 初始化日志
        setup_logger()
        logging.info("应用程序初始化开始")
        
        # 创建主水平布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        
        # ====================== 左侧选项卡区域 ======================
        left_frame = QFrame()
        left_frame.setFixedWidth(120)
        left_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 8px;")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(5, 15, 5, 15)
        left_layout.setSpacing(5)
        
        # 创建左侧选项卡按钮
        self.home_btn = VerticalTabButton(self._("home"))
        self.home_btn.setChecked(True)
        self.home_btn.clicked.connect(lambda: self.switch_tab(0))
        
        self.progress_btn = VerticalTabButton(self._("progress"))
        self.progress_btn.clicked.connect(lambda: self.switch_tab(1))
        
        self.record_btn = VerticalTabButton(self._("history"))
        self.record_btn.clicked.connect(lambda: self.switch_tab(2))
        
        left_layout.addWidget(self.home_btn)
        left_layout.addWidget(self.progress_btn)
        left_layout.addWidget(self.record_btn)
        left_layout.addStretch()
        
        # ====================== 右侧区域 ======================
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: #ffffff; border-radius: 8px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建堆叠窗口
        self.stacked_widget = QStackedWidget()
        
        # 主页面 (索引0)
        home_page = QWidget()
        home_layout = QVBoxLayout(home_page)
        home_layout.setContentsMargins(20, 20, 20, 20)
        home_layout.setSpacing(15)
        
        # 标题
        title = QLabel(self._("app_title"))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #212529; margin-bottom: 10px;")
        
        # 创建右侧上方的二级选项卡
        self.top_tab_widget = QTabWidget()
        self.top_tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.top_tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background: #e9ecef;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: 500;
                color: #495057;
            }
            QTabBar::tab:selected {
                background: white;
                color: #212529;
                font-weight: 600;
                border-bottom: 2px solid #4CAF50;
            }
            QTabBar::tab:hover {
                background: #dee2e6;
            }
        """)
        
        # 单本下载选项卡
        single_download_tab = QWidget()
        single_layout = QVBoxLayout(single_download_tab)
        single_layout.setContentsMargins(15, 15, 15, 15)
        
        # 单本下载输入框
        self.novel_id_input = QLineEdit()
        self.novel_id_input.setPlaceholderText(self._("input_placeholder"))
        self.novel_id_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
        """)
        self.novel_id_input.setMinimumHeight(40)
        
        # 单本下载按钮
        download_btn = QPushButton(self._("download_btn"))
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        download_btn.setMinimumHeight(40)
        # 关键修复：使用lambda忽略信号参数
        download_btn.clicked.connect(lambda: self.download_novel())
        
        single_layout.addWidget(QLabel(self._("input_placeholder") + ":"))
        single_layout.addWidget(self.novel_id_input)
        single_layout.addSpacing(10)
        single_layout.addWidget(download_btn)
        single_layout.addStretch()
        
        self.top_tab_widget.addTab(single_download_tab, self._("single_download"))
        
        # 批量下载选项卡
        batch_download_tab = QWidget()
        batch_layout = QVBoxLayout(batch_download_tab)
        batch_layout.setContentsMargins(15, 15, 15, 15)
        
        # 批量下载输入框
        self.batch_input = QTextEdit()
        self.batch_input.setPlaceholderText(self._("batch_input_placeholder"))
        # 关键设置：禁用自动格式化，只接受纯文本
        self.batch_input.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoNone)
        self.batch_input.setAcceptRichText(False)
        self.batch_input.setStyleSheet("""
        QTextEdit {
            padding: 10px;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 14px;
            text-decoration: none; /* 移除下划线 */
            }
        QTextEdit:focus {
            border: 1px solid #86b7fe;
        }
        """)
        self.batch_input.setMinimumHeight(100)
        
        # 批量下载按钮
        batch_download_btn = QPushButton(self._("batch_download_btn"))
        batch_download_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #8e24aa;
            }
            QPushButton:pressed {
                background-color: #7b1fa2;
            }
        """)
        batch_download_btn.setMinimumHeight(40)
        # 关键修复：使用lambda忽略信号参数
        batch_download_btn.clicked.connect(lambda: self.batch_download())
        
        batch_layout.addWidget(QLabel(self._("batch_input_placeholder") + ":"))
        batch_layout.addWidget(self.batch_input)
        batch_layout.addSpacing(10)
        batch_layout.addWidget(batch_download_btn)
        batch_layout.addStretch()
        
        self.top_tab_widget.addTab(batch_download_tab, self._("batch_download"))
        
        # 设置按钮
        settings_btn = QPushButton(self._("settings_btn"))
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1e88e5;
            }
            QPushButton:pressed {
                background-color: #1976d2;
            }
        """)
        settings_btn.setMinimumHeight(40)
        # 关键修复：使用lambda忽略信号参数
        settings_btn.clicked.connect(lambda: self.open_settings())
        
        # 添加到主页布局
        home_layout.addWidget(title)
        home_layout.addWidget(self.top_tab_widget, 1)
        home_layout.addWidget(settings_btn)
        
        # 进度页面 (索引1)
        progress_page = QWidget()
        progress_layout = QVBoxLayout(progress_page)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        
        # 进度标题
        progress_title = QLabel(self._("progress_title"))
        progress_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #212529; margin-bottom: 20px;")
        progress_layout.addWidget(progress_title)
        
        # 进度标签
        self.progress_label = QLabel(self._("status_idle"))
        self.progress_label.setStyleSheet("color: #6c757d; margin-bottom: 5px; font-size: 14px;")
        progress_layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet("""
            QProgressBar {
                height: 25px;
                border: 1px solid #dee2e6;
                border-radius: 12px;
                text-align: center;
                background: white;
                font-size: 14px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 12px;
            }
        """)
        progress_layout.addWidget(self.progress)
        
        # 进度信息
        self.progress_info = QLabel(self._("waiting_task"))
        self.progress_info.setStyleSheet("color: #6c757d; margin-top: 15px; font-size: 13px;")
        progress_layout.addWidget(self.progress_info)
        
        # 返回主页按钮
        back_btn = QPushButton(self._("back_home"))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-weight: 500;
                margin-top: 30px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        back_btn.setMinimumHeight(40)
        back_btn.clicked.connect(lambda: self.switch_tab(0))
        progress_layout.addStretch()
        progress_layout.addWidget(back_btn)
        
        # 下载记录页面 (索引2)
        record_page = QWidget()
        record_layout = QVBoxLayout(record_page)
        record_layout.setContentsMargins(20, 20, 20, 20)
        
        # 下载记录标题
        record_title = QLabel(self._("history_title"))
        record_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #212529; margin-bottom: 20px;")
        record_layout.addWidget(record_title)
        
        # 下载记录列表
        self.download_list = QListWidget()
        self.download_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #dee2e6;
            }
            QListWidget::item:selected {
                background-color: #e6f7e9;
                color: #212529;
            }
        """)
        record_layout.addWidget(self.download_list, 1)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        # 清空记录按钮
        clear_btn = QPushButton(self._("clear_history"))
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(self.clear_download_history)
        
        # 返回主页按钮
        back_btn2 = QPushButton(self._("back_home"))
        back_btn2.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 10px;
                border-radius: 6px;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        back_btn2.setMinimumHeight(40)
        back_btn2.clicked.connect(lambda: self.switch_tab(0))
        
        btn_layout.addWidget(clear_btn)
        btn_layout.addWidget(back_btn2)
        record_layout.addLayout(btn_layout)
        
        # 添加页面到堆叠窗口
        self.stacked_widget.addWidget(home_page)
        self.stacked_widget.addWidget(progress_page)
        self.stacked_widget.addWidget(record_page)
        
        right_layout.addWidget(self.stacked_widget)
        
        # 添加左右部件到主布局
        main_layout.addWidget(left_frame, 0)  # 左侧固定宽度
        main_layout.addWidget(right_frame, 1)  # 右侧自适应
        
        # 加载保存路径和文件格式
        self.save_path = self.settings.value("save_path", "downloads", type=str)
        self.file_format = self.settings.value("file_format", "TXT", type=str)
        self.open_after_download = self.settings.value("open_after_download", True, type=bool)
        
        # 初始化下载记录
        self.load_download_history()
        
        logging.info("应用程序初始化完成")
    
    def switch_tab(self, index):
        """切换右侧页面"""
        self.stacked_widget.setCurrentIndex(index)
        
        # 更新按钮选中状态
        self.home_btn.setChecked(index == 0)
        self.progress_btn.setChecked(index == 1)
        self.record_btn.setChecked(index == 2)
    
    def load_download_history(self):
        """加载下载历史记录"""
        logging.debug("开始加载下载历史记录")
        history = self.settings.value("download_history", [])
        for item in history:
            self.download_list.addItem(item)
        logging.debug(f"加载了 {len(history)} 条下载历史记录")
    
    def save_download_history(self, title):
        """保存下载历史记录"""
        # 添加时间戳
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        item_text = f"{timestamp} - {title}"
        
        # 添加到列表
        self.download_list.insertItem(0, item_text)
        
        # 保存到设置
        history = self.settings.value("download_history", [])
        history.insert(0, item_text)
        # 只保留最近的20条记录
        if len(history) > 20:
            history = history[:20]
        self.settings.setValue("download_history", history)
        logging.info(f"保存下载历史记录: {title}")
    
    def clear_download_history(self):
        """清空下载历史记录"""
        logging.info("用户请求清空下载历史记录")
        reply = QMessageBox.question(self, self._("confirm_title"), self._("confirm_clear"),
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_list.clear()
            self.settings.setValue("download_history", [])
            logging.info("已清空下载历史记录")
    
    def open_settings(self):
        logging.debug("打开设置对话框")
        dialog = SettingsDialog(self)
        if dialog.exec():
            # 更新设置
            self.save_path = dialog.save_path_input.text()
            format_text = dialog.format_combo.currentText()
            if "TXT" in format_text:
                self.file_format = "TXT"
            elif "HTML" in format_text:
                self.file_format = "HTML"
            elif "Markdown" in format_text:
                self.file_format = "Markdown"
            
            self.open_after_download = dialog.open_folder_checkbox.isChecked()
            
            # 更新语言设置
            new_lang = dialog.language_combo.currentData()
            if new_lang != self.translator.language:
                self.settings.setValue("language", new_lang)
                logging.info(f"语言设置已更新: {new_lang}")
                QMessageBox.information(self, self._("settings_title"), 
                                       self._("batch_success", success="", total="") + "\n" + self._("restart_required"))
            
            # 保存设置
            self.settings.setValue("save_path", self.save_path)
            self.settings.setValue("file_format", self.file_format)
            self.settings.setValue("open_after_download", self.open_after_download)
            
            logging.info(f"设置已更新: 保存路径={self.save_path}, 文件格式={self.file_format}, 下载后打开文件夹={self.open_after_download}")
    
    def extract_content_id(self, input_text):
        """从输入中提取内容ID和类型"""
        # 清除前后空格
        input_text = input_text.strip()
        logging.debug(f"提取内容ID: 输入文本: '{input_text}'")
        
        # 支持多种URL格式的正则表达式
        patterns = [
            r'novel/show\.php\?id=(\d+)',        # 旧版URL
            r'novel/.*?id=(\d+)',                 # 带参数的URL
            r'novel/(\d+)',                       # 新版URL
            r'n/(\d+)',                           # 短链接
            r'series/(\d+)',                      # 系列URL
            r'works/(\d+)',                       # 作品URL（可能包含小说）
            r'id=(\d+)',                          # 直接ID参数
            r'^(\d+)$'                            # 纯数字ID
        ]
        
        # 尝试匹配所有模式
        for pattern in patterns:
            match = re.search(pattern, input_text)
            if match:
                content_id = match.group(1)
                
                # 确定内容类型
                if 'series' in pattern:
                    result = ("series", content_id)
                else:
                    result = ("novel", content_id)
                
                logging.debug(f"匹配成功: 模式 '{pattern}' -> 类型 '{result[0]}', ID '{result[1]}'")
                return result
        
        # 如果没有匹配任何模式，抛出详细错误
        error_msg = self._("extract_error", input=input_text)
        logging.warning(error_msg)
        raise ValueError(error_msg)
            
    def open_after_download(self):
      # 根据下载模式决定是否立即打开
      if self.is_batch_download or self.is_series_download:
        self.open_after_download=True
      else:
        self.open_after_download=False

    def open_folder(self,file_path,open_folder=True):
       # 如果设置了下载后打开文件夹 且 open_folder=True
            if open_folder:
                try:
                    # 打开文件所在目录
                    if sys.platform == "win32":
                        os.startfile(os.path.dirname(file_path))
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", os.path.dirname(file_path)])
                    else:
                        subprocess.Popen(["xdg-open", os.path.dirname(file_path)])
                    logging.info(f"已打开文件夹: {os.path.dirname(file_path)}")
                except Exception as e:
                    logging.error(f"打开文件夹失败: {str(e)}")
            else:
                logging.info("用户选择不自动打开文件夹")
            
    def download_novel(self, novel_id=None):
        """下载单本小说或系列"""
        try:
            logging.info("开始下载小说")
            
            # 切换到进度页面
            self.switch_tab(1)
            
            # 关键修复：确保novel_id不是布尔值False
            if novel_id is False:
                logging.error("检测到无效的布尔值False作为novel_id参数")
                QMessageBox.critical(self, self._("error"), self._("invalid_id"))
                return
                
            if novel_id is None:
                input_text = self.novel_id_input.text().strip()
                if not input_text:
                    logging.warning("单本下载输入为空")
                    QMessageBox.warning(self, self._("warning"), self._("input_empty"))
                    return
                
                logging.info(f"单本下载输入: '{input_text}'")
                    
                # 从链接中提取ID
                result = self.extract_content_id(input_text)
                content_type, content_id = result
                
                # 验证ID格式
                if not content_id.isdigit():
                    error_msg = self._("invalid_id", id=content_id)
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                
                logging.info(f"开始下载: 类型 '{content_type}', ID '{content_id}'")
                
                if content_type == "novel":
                    self.download_single_novel(content_id)
                elif content_type == "series":
                    self.download_series(content_id)
            else:
                # 确保传入的是字符串
                novel_id_str = str(novel_id)
                
                # 关键修复：防止布尔值False被转换为字符串'False'
                if novel_id_str == "False":
                    logging.error("检测到字符串'False'作为小说ID")
                    QMessageBox.critical(self, self._("error"), self._("invalid_id", id=novel_id_str))
                    return
                
                # 验证传入的novel_id是否为有效数字
                if not novel_id_str.isdigit():
                    error_msg = self._("invalid_id", id=novel_id_str)
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                
                logging.info(f"开始下载小说: ID '{novel_id_str}'")
                self.download_single_novel(novel_id_str)
                
            logging.info("下载任务完成")
        except Exception as e:
            error_msg = f"{self._('download_failed')}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            QMessageBox.critical(self, self._("error"), error_msg)
        
    def download_single_novel(self, novel_id):
        """下载单本小说"""
        try:
            # 验证ID格式
            if not isinstance(novel_id, str) or not novel_id.isdigit():
                error_msg = self._("invalid_id", id=novel_id)
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            logging.info(f"开始下载单本小说: ID {novel_id}")
            
            # 更新进度状态
            self.progress.setValue(0)
            self.progress_label.setText(self._("status_downloading"))
            self.progress_info.setText(self._("getting_info", id=novel_id))
            QApplication.processEvents()
            
            # 获取小说信息 - 使用正确的API端点
            url = f"https://www.pixiv.net/ajax/novel/{novel_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.pixiv.net/"
            }
            
            logging.debug(f"请求小说API: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            logging.debug(f"API响应状态码: {response.status_code}")
            
            # 检查响应内容
            if response.status_code == 404:
                error_msg = self._("novel_not_found", id=novel_id)
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # 尝试解析JSON响应
            try:
                novel_data = response.json()
                # 只记录部分响应，避免日志过大
                log_data = {k: v for k, v in novel_data.items() if k != "body"}
                logging.debug(f"API响应: {json.dumps(log_data, ensure_ascii=False)}")
            except json.JSONDecodeError:
                error_msg = self._("invalid_response")
                logging.error(error_msg, exc_info=True)
                raise Exception(error_msg)
            
            if novel_data.get("error"):
                error_msg = novel_data["error"].get("message", self._("api_error"))
                logging.error(f"API返回错误: {error_msg}")
                QMessageBox.critical(self, self._("error"), error_msg)
                return
            
            # 检查响应结构
            if not novel_data.get("body"):
                error_msg = self._("invalid_response")
                logging.error(error_msg)
                QMessageBox.critical(self, self._("error"), error_msg)
                return
            
            # 创建下载目录
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)
                logging.info(f"创建下载目录: {self.save_path}")
            
            # 下载小说
            novel_title = novel_data["body"].get("title", "未命名小说")
            novel_content = novel_data["body"].get("content", "")
            
            logging.info(f"获取小说成功: 《{novel_title}》, 内容长度: {len(novel_content)} 字符")
            
            # 更新进度
            self.progress.setValue(30)
            self.progress_info.setText(self._("saving_novel", title=novel_title))
            QApplication.processEvents()
            
            # 根据选择的格式保存小说
            if self.file_format == "HTML":
                escaped_title = novel_title.replace('"', '&quot;')
                formatted_content = novel_content.replace('\n', '<br>')
                content = f"<html><head><title>{escaped_title}</title></head><body><h1>{escaped_title}</h1><div>{formatted_content}</div></body></html>"
                ext = "html"
            elif self.file_format == "Markdown":
                content = f"# {novel_title}\n\n{novel_content}"
                ext = "md"
            else:  # TXT
                content = novel_content
                ext = "txt"
                
            # 清理文件名中的非法字符
            safe_title = re.sub(r'[\\/*?:"<>|]', "", novel_title)
            file_path = os.path.join(self.save_path, f"{safe_title}.{ext}")
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logging.info(f"小说保存成功: {file_path}")
            
            # 更新进度和下载记录
            self.progress.setValue(100)
            self.progress_label.setText(self._("status_completed"))
            self.progress_info.setText(self._("completed", title=novel_title))
            self.save_download_history(novel_title)
            self.open_folder(file_path,open_folder=True)
            
        except Exception as e:
            error_msg = f"{self._('download_failed')}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            QMessageBox.critical(self, self._("error"), error_msg)
            self.progress.setValue(0)
            self.progress_label.setText(self._("status_error"))
            self.progress_info.setText(f"{self._('download_failed')}: {str(e)}")
             # 显示成功消息并返回主页
            QMessageBox.information(self, self._("download_success", title=novel_title), 
                                   self._("download_success", title=novel_title))
            self.switch_tab(0)

    def download_series(self, series_id):
        """下载整个系列"""
        try:
            # 验证ID格式
            if not isinstance(series_id, str) or not series_id.isdigit():
                error_msg = self._("invalid_id", id=series_id)
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            logging.info(f"开始下载系列: ID {series_id}")
            
            # 更新进度状态
            self.progress.setValue(0)
            self.progress_label.setText(self._("status_downloading"))
            self.progress_info.setText(self._("series_info", id=series_id))
            QApplication.processEvents()
            
            # 获取系列信息
            url = f"https://www.pixiv.net/ajax/novel/series/{series_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.pixiv.net/"
            }
            
            logging.debug(f"请求系列API: {url}")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            logging.debug(f"API响应状态码: {response.status_code}")
            
            if response.status_code == 404:
                error_msg = self._("series_not_found", id=series_id)
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # 解析JSON响应
            try:
                series_data = response.json()
                # 记录完整响应
                logging.debug(f"完整API响应: {json.dumps(series_data, ensure_ascii=False)[:1000]}...")
            except json.JSONDecodeError:
                error_msg = self._("invalid_response")
                logging.error(error_msg, exc_info=True)
                raise Exception(error_msg)
            
            if series_data.get("error"):
                error_msg = series_data["error"].get("message", self._("api_error"))
                logging.error(f"API返回错误: {error_msg}")
                QMessageBox.critical(self, self._("error"), error_msg)
                return
            
            # 检查响应结构
            if not series_data.get("body"):
                error_msg = self._("invalid_response")
                logging.error(error_msg)
                QMessageBox.critical(self, self._("error"), error_msg)
                return
            
            # 获取系列标题
            series_title = series_data["body"].get("title", "未命名系列")
            logging.info(f"获取系列成功: 《{series_title}》")
            
            # 使用系列内容API获取小说ID列表
            novel_ids = []
            
            # 尝试直接使用系列API中的内容
            contents = series_data["body"].get("seriesContents", {}).get("contents", [])
            if contents:
                for item in contents:
                    if isinstance(item, dict) and "id" in item:
                        novel_id = str(item["id"])
                        if novel_id.isdigit() and int(novel_id) > 0:
                            novel_ids.append(novel_id)
                            logging.debug(f"从主API添加小说ID: {novel_id}")
            
            # 如果主API中没有内容，尝试系列内容API
            if not novel_ids:
                logging.info("主API未返回内容，尝试系列内容API")
                try:
                    # 系列内容API端点
                    content_url = f"https://www.pixiv.net/ajax/novel/series_content/{series_id}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Referer": "https://www.pixiv.net/"
                    }
                    
                    logging.debug(f"请求系列内容API: {content_url}")
                    content_response = requests.get(content_url, headers=headers)
                    content_response.raise_for_status()
                    
                    # 解析JSON响应
                    content_data = content_response.json()
                    logging.debug(f"内容API响应: {json.dumps(content_data, ensure_ascii=False)[:1000]}...")
                    
                    if not content_data.get("error") and content_data.get("body"):
                        # 从内容API提取小说ID
                        contents = content_data["body"].get("page", {}).get("seriesContents", [])
                        for item in contents:
                            if isinstance(item, dict) and "id" in item:
                                novel_id = str(item["id"])
                                if novel_id.isdigit() and int(novel_id) > 0:
                                    novel_ids.append(novel_id)
                                    logging.debug(f"从内容API添加小说ID: {novel_id}")
                except Exception as e:
                    logging.warning(f"获取系列内容失败: {str(e)}")
            
            # 如果仍然没有小说ID，尝试从系列描述中提取
            if not novel_ids:
                logging.info("尝试从描述中提取小说ID")
                caption = series_data["body"].get("caption", "")
                # 使用正则表达式查找可能的ID
                id_matches = re.findall(r'\b\d{7,9}\b', caption)
                for id_str in id_matches:
                    if id_str not in novel_ids:
                        novel_ids.append(id_str)
                        logging.debug(f"从描述中提取小说ID: {id_str}")
            
            # 最终检查
            if not novel_ids:
                error_msg = f"系列《{series_title}》中没有找到有效的小说ID"
                logging.warning(error_msg)
                QMessageBox.warning(self, self._("warning"), error_msg)
                return
            
            logging.info(f"系列中包含 {len(novel_ids)} 个小说ID")
            
            # 创建系列目录
            safe_series_title = re.sub(r'[\\/*?:"<>|]', "", series_title)
            series_dir = os.path.join(self.save_path, safe_series_title)
            if not os.path.exists(series_dir):
                os.makedirs(series_dir)
                logging.info(f"创建系列目录: {series_dir}")
            
            # 保存原始保存路径
            original_save_path = self.save_path
            self.save_path = series_dir
            
            # 批量下载系列中的小说
            total = len(novel_ids)
            self.progress_label.setText(self._("series_progress", title=series_title))
            self.progress.setValue(0)
            self.is_series_download=True
            
            success_count = 0
            for i, novel_id in enumerate(novel_ids):
                progress = int((i / total) * 100)
                self.progress.setValue(progress)
                self.progress_info.setText(self._("batch_progress", current=i+1, total=total, id=novel_id))
                QApplication.processEvents()  # 更新UI
                
                try:
                    # 验证ID格式
                    if not isinstance(novel_id, str) or not novel_id.isdigit():
                        error_msg = self._("invalid_id", id=novel_id)
                        logging.warning(error_msg)
                        raise ValueError(error_msg)
                    
                    logging.info(f"下载系列中的小说 {i+1}/{total}: ID {novel_id}")
                    self.download_single_novel(novel_id)
                    success_count += 1
                    logging.info(f"小说 {novel_id} 下载成功")
                    self.is_series_download=False
                except Exception as e:
                    error_msg = f"小说 {novel_id} 下载失败: {str(e)}"
                    logging.error(error_msg, exc_info=True)
                    self.progress_info.setText(error_msg)
                
                # 更新进度
                self.progress.setValue(int(((i+1) / total) * 100))
                QApplication.processEvents()
            
            # 恢复原始保存路径
            self.save_path = original_save_path
            
            self.progress.setValue(100)
            self.progress_label.setText(self._("status_completed"))
            self.progress_info.setText(self._("series_completed", title=series_title, success=success_count, total=total))
            self.save_download_history(f"系列: {series_title}")
            
        except Exception as e:
            error_msg = f"{self._('download_failed')}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            QMessageBox.critical(self, self._("error"), error_msg)
            self.progress.setValue(0)
            self.progress_label.setText(self._("status_error"))
            self.progress_info.setText(f"{self._('download_failed')}: {str(e)}")
    
    def get_series_content(self, series_id):
        """使用系列内容API获取小说ID列表"""
        novel_ids = []
        try:
            # 系列内容API端点
            url = f"https://www.pixiv.net/ajax/novel/series_content/{series_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": "https://www.pixiv.net/"
            }
            
            # 分页参数
            limit = 100
            offset = 0
            total = float('inf')  # 初始化为无穷大，直到获取到实际总数
            
            while offset < total:
                params = {
                    "limit": limit,
                    "offset": offset,
                    "order": "asc"  # 确保顺序正确
                }
                
                logging.debug(f"请求系列内容API: {url}?limit={limit}&offset={offset}")
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                # 解析JSON响应
                content_data = response.json()
                logging.debug(f"内容API响应: {json.dumps(content_data, ensure_ascii=False)[:1000]}...")
                
                if content_data.get("error"):
                    error_msg = content_data["error"].get("message", self._("api_error"))
                    logging.error(f"内容API返回错误: {error_msg}")
                    break
                
                # 检查响应结构
                if not content_data.get("body"):
                    logging.error("内容API响应格式不正确")
                    break
                
                # 获取总项目数
                if total == float('inf'):
                    total = content_data["body"].get("total", 0)
                    logging.info(f"系列总项目数: {total}")
                
                # 提取小说ID
                contents = content_data["body"].get("page", {}).get("seriesContents", [])
                for item in contents:
                    if isinstance(item, dict) and "id" in item:
                        novel_id = str(item["id"])
                        if novel_id.isdigit() and int(novel_id) > 0:
                            novel_ids.append(novel_id)
                            logging.debug(f"添加小说ID: {novel_id}")
                
                # 更新偏移量
                offset += len(contents)
                
                # 如果没有更多内容或已获取所有项目，退出循环
                if not contents or offset >= total:
                    break
            
            logging.info(f"获取到 {len(novel_ids)} 个小说ID")
            return novel_ids
            
        except Exception as e:
            logging.error(f"获取系列内容失败: {str(e)}", exc_info=True)
            return []
        
    def batch_download(self):
        """批量下载多个小说或系列"""
        try:
            logging.info("开始批量下载")
            input_text = self.batch_input.toPlainText().strip()
            if not input_text:
                logging.warning("批量下载输入为空")
                QMessageBox.warning(self, self._("warning"), self._("batch_input_empty"))
                return
                
            logging.info(f"批量下载输入: '{input_text}'")
            
            # 切换到进度页面
            self.switch_tab(1)
            
            # 分割输入为多行
            items = [line.strip() for line in input_text.split('\n') if line.strip()]
            logging.info(f"解析到 {len(items)} 个输入项")
            
            # 提取所有有效ID
            content_ids = []
            errors = []
            
            for i, item in enumerate(items, 1):
                try:
                    result = self.extract_content_id(item)
                    content_ids.append(result)
                    logging.debug(f"第 {i} 行: 有效内容 '{item}' -> 类型 '{result[0]}', ID '{result[1]}'")
                except Exception as e:
                    error_msg = f"第 {i} 行: {str(e)}"
                    errors.append(error_msg)
                    logging.warning(error_msg)
                    
            # 显示所有错误
            if errors:
                error_msg = "\n".join(errors)
                logging.warning(f"批量下载输入错误: {error_msg}")
                QMessageBox.warning(self, self._("error"), f"{self._('invalid_input')}:\n\n{error_msg}")
                    
            if not content_ids:
                logging.warning("批量下载中没有找到有效的内容ID")
                QMessageBox.warning(self, self._("warning"), self._("no_valid_ids"))
                return
                
            logging.info(f"开始批量下载 {len(content_ids)} 个项目")
            
            # 批量下载
            total = len(content_ids)
            self.progress_label.setText(self._("status_downloading"))
            self.progress.setValue(0)
            self.is_batch_download=True
            
            success_count = 0
            for i, (content_type, content_id) in enumerate(content_ids):
                progress = int((i / total) * 100)
                self.progress.setValue(progress)
                self.progress_info.setText(self._("batch_progress", current=i+1, total=total, id=content_id))
                QApplication.processEvents()  # 更新UI
                
                try:
                    # 验证ID格式
                    if not isinstance(content_id, str) or not content_id.isdigit():
                        error_msg = self._("invalid_id", id=content_id)
                        logging.warning(error_msg)
                        raise ValueError(error_msg)
                    
                    logging.info(f"下载项目 {i+1}/{total}: 类型 '{content_type}', ID '{content_id}'")
                    
                    if content_type == "novel":
                        # 下载单本小说时不打开文件夹
                        self.download_single_novel(content_id)
                        success_count += 1
                        self.is_series_download=False
                    elif content_type == "series":
                        # 下载整个系列时不打开文件夹
                        self.download_series(content_id)
                        success_count += 1
                    logging.info(f"项目 {i+1}/{total} 下载成功")
                except Exception as e:
                    error_msg = f"内容 {content_id} 下载失败: {str(e)}"
                    logging.error(error_msg, exc_info=True)
                    self.progress_info.setText(error_msg)
                
                # 更新进度
                self.progress.setValue(int(((i+1) / total) * 100))
                QApplication.processEvents()
            
            self.progress.setValue(100)
            self.progress_label.setText(self._("status_completed"))
            self.progress_info.setText(self._("batch_success", success=success_count, total=total))
            # 显示成功消息并返回主页
            QMessageBox.information(self, self._("batch_success", success=success_count, total=total), 
                                   self._("batch_success", success=success_count, total=total))
            self.switch_tab(0)
            self.is_batch_download=False
            logging.info(f"批量下载完成! 成功: {success_count}/{total}")
            
        except Exception as e:
            error_msg = f"{self._('download_failed')}: {str(e)}"
            logging.error(error_msg, exc_info=True)
            QMessageBox.critical(self, self._("error"), error_msg)
            self.progress.setValue(0)
            self.progress_label.setText(self._("status_error"))
            self.progress_info.setText(f"{self._('download_failed')}: {str(e)}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._ = parent.translator.translate
        self.setWindowTitle(self._("settings_title"))
        self.setFixedSize(600, 850)  # 增加高度以容纳更多内容
        
        # 设置对话框样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
                border-radius: 10px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QLabel {
                color: #495057;
                font-size: 14px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                min-height: 36px;
                font-size: 14px;
            }
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
            }
            QLineEdit, QComboBox {
                min-height: 40px;
                padding: 8px 12px;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                width: 30px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        #layout.setSpacing(15)
        
        # 标题
        title = QLabel(self._("settings_title"))
        title.setStyleSheet("""
            font-size: 18px; 
            font-weight: bold; 
            color: #212529; 
            margin-bottom: 10px;
            qproperty-alignment: 'AlignCenter';
        """)
        layout.addWidget(title)
        
        # 保存路径设置
        save_path_frame = QFrame()
        save_path_layout = QVBoxLayout(save_path_frame)
        # save_path_layout.setSpacing(10)
        
        save_path_label = QLabel(self._("save_path"))
        save_path_label.setStyleSheet("font-weight: 500;")
        
        path_layout = QHBoxLayout()
        # path_layout.setSpacing(10)
        self.save_path_input = QLineEdit()
        self.save_path_input.setText(parent.save_path)
        self.save_path_input.setMinimumHeight(40)
        
        browse_btn = QPushButton(self._("browse"))
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #e9ecef;
                color: #495057;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #dee2e6;
            }
        """)
        browse_btn.setMinimumHeight(40)
        browse_btn.clicked.connect(self.browse_folder)
        
        path_layout.addWidget(self.save_path_input, 4)
        path_layout.addWidget(browse_btn, 1)
        
        save_path_layout.addWidget(save_path_label)
        save_path_layout.addLayout(path_layout)
        
        # 文件格式设置
        format_frame = QFrame()
        format_layout = QVBoxLayout(format_frame)
        # format_layout.setSpacing(10)
        
        format_label = QLabel(self._("file_format"))
        format_label.setStyleSheet("font-weight: 500;")
        
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            self._("format_txt"),
            self._("format_html"),
            self._("format_md")
        ])
        self.format_combo.setCurrentIndex(["TXT", "HTML", "Markdown"].index(parent.file_format))
        self.format_combo.setMinimumHeight(40)
        
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        
        # 语言设置
        language_frame = QFrame()
        language_layout = QVBoxLayout(language_frame)
        # language_layout.setSpacing(10)
        
        language_label = QLabel(self._("language"))
        language_label.setStyleSheet("font-weight: 500;")
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_cn")
        self.language_combo.addItem("English", "en_us")
        self.language_combo.addItem("日本語", "ja_jp")
        self.language_combo.setCurrentIndex(0 if parent.translator.language == "zh_cn" else 1 if parent.translator.language == "en_us" else 2)
        self.language_combo.setMinimumHeight(40)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        
        # 下载后打开文件夹设置
        open_folder_frame = QFrame()
        open_folder_layout = QVBoxLayout(open_folder_frame)
        # open_folder_layout.setSpacing(10)
        
        open_folder_label = QLabel(self._("post_download"))
        open_folder_label.setStyleSheet("font-weight: 500;")
        
        self.open_folder_checkbox = QCheckBox(self._("open_folder"))
        self.open_folder_checkbox.setChecked(parent.open_after_download)
        self.open_folder_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 8px 0;
                font-size: 14px;
            }
        """)
        
        open_folder_layout.addWidget(open_folder_label)
        open_folder_layout.addWidget(self.open_folder_checkbox)
        
        # 添加一些垂直间距
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # 保存按钮
        save_btn = QPushButton(self._("save_settings"))
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                min-height: 40px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.setMinimumHeight(45)
        save_btn.clicked.connect(self.accept)
        
        # 添加到布局
        layout.addWidget(save_path_frame)
        layout.addWidget(format_frame)
        layout.addWidget(language_frame)
        layout.addWidget(open_folder_frame)
        layout.addWidget(spacer)  # 添加弹性空间
        layout.addWidget(save_btn, 0, Qt.AlignmentFlag.AlignRight)
        
        # 设置高度策略
        self.save_path_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.format_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.language_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    def accept(self):
        # 保存设置
        self.parent.settings.setValue("save_path", self.save_path_input.text())
        format_text = self.format_combo.currentText()
        if "TXT" in format_text:
            self.parent.file_format = "TXT"
        elif "HTML" in format_text:
            self.parent.file_format = "HTML"
        elif "Markdown" in format_text:
            self.parent.file_format = "Markdown"
        
        self.parent.open_after_download = self.open_folder_checkbox.isChecked()
        
        # 新增语言变更检查
        new_lang = self.language_combo.currentData()
        if new_lang != self.parent.translator.language:
            self.parent.settings.setValue("language", new_lang)
            QMessageBox.information(
                self, 
                self._("settings_title"),
                self._("restart_required"),
                QMessageBox.StandardButton.Ok
            )
            QApplication.exit(201)
            
        super().accept()

    def browse_folder(self):
        logging.debug("浏览保存路径")
        folder = QFileDialog.getExistingDirectory(self, self._("browse"))
        if folder:
            self.save_path_input.setText(folder)
            logging.info(f"选择保存路径: {folder}")

if __name__ == "__main__":
    restart_count = 0
    max_restart_attempts = 3  # 最大重启尝试次数
    
    while True:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # 设置全局样式
        app.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f7;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QWidget {
                font-size: 14px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 8px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #86b7fe;
            }
            QLabel {
                color: #495057;
            }
            QFrame {
                background-color: white;
                border-radius: 8px;
            }
        """)
        
        window = PixivNovelDownloader()
        if os.path.exists("icon.ico"):
            window.setWindowIcon(QIcon("icon.ico"))
        window.show()
        exit_code = app.exec()
        
        # 检查是否需要重启
        if exit_code == 201:  # 重启退出码
            restart_count += 1
            logging.info(f"尝试重启程序 (尝试次数: {restart_count}/{max_restart_attempts})")
            
            if restart_count > max_restart_attempts:
                logging.error("达到最大重启尝试次数，退出程序")
                break
                
            # 在打包环境中，使用可执行文件路径
            if getattr(sys, 'frozen', False):
                # 在打包环境中
                executable_path = sys.executable
                logging.info(f"打包环境重启: {executable_path}")
                
                try:
                    # 对于Windows系统
                    if sys.platform == "win32":
                        # 使用绝对路径启动新进程
                        subprocess.Popen([executable_path])
                        sys.exit(0)
                    
                    # 对于macOS系统
                    elif sys.platform == "darwin":
                        # macOS可能需要指定.app包路径
                        if executable_path.endswith('.app'):
                            # 如果是在.app包中
                            app_path = os.path.dirname(executable_path)
                            subprocess.Popen(['open', app_path])
                        else:
                            subprocess.Popen([executable_path])
                        sys.exit(0)
                    
                    # 对于Linux系统
                    else:
                        subprocess.Popen([executable_path])
                        sys.exit(0)
                except Exception as e:
                    logging.error(f"重启失败: {str(e)}")
                    break
            else:
                # 在开发环境中
                logging.info("开发环境重启")
                try:
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                except Exception as e:
                    logging.error(f"重启失败: {str(e)}")
                    break
        else:
            # 正常退出
            break
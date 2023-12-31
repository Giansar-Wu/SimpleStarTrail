import os
import datetime
import sys
from threading import Thread

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QGuiApplication, QTextCursor, QFont
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QGridLayout, QLineEdit, QComboBox, QLabel, QFileDialog, QPushButton, QTextEdit, QSpinBox, QMessageBox, QProgressBar, QDoubleSpinBox

import startrail

class MyMainWindow(QMainWindow):
    progress_signal = Signal(int)

    def __init__(self):
        super().__init__()
        screen = QGuiApplication.primaryScreen().geometry()
        self.setWindowTitle('SimpleStarTrail')
        self.setFixedSize(int(screen.width()/2.7), int(screen.height()/2.7))
        icon = QIcon()
        icon.addFile(os.path.join(startrail.ROOT_PATH, "resources", "icons", "星星.png"))
        self.setWindowIcon(icon)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.agent = startrail.StarTrailAgent()
        self._init_ui()
        self._connect()

        self.stream = Stream()
        self.stream.stream_update.connect(self._write_log_info)
        sys.stdout = self.stream
        sys.stderr = self.stream

        self.stream_update_state = 0
        print(F"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] SimpleStarTrail start!")

    def _init_ui(self):
        cols = 6
        self.central_layout = QGridLayout(self.central_widget)
        self.central_widget.setLayout(self.central_layout)

        for i in range(cols):
            self.central_layout.setColumnMinimumWidth(i, 1)
            self.central_layout.setColumnStretch(i, 1)

        # input display
        self.input_display = QLineEdit(self.central_widget)
        self.input_display.setReadOnly(True)
        self.input_display.setText("请选择要导入的文件夹")
        font = QFont()
        font.setItalic(True)
        self.input_display.setFont(font)
        self.central_layout.addWidget(self.input_display, 0, 0, 1, 5)

        # images path select button
        self.images_path_select_button = QPushButton(self.central_widget)
        self.images_path_select_button.setText("选择文件夹")
        self.central_layout.addWidget(self.images_path_select_button, 0, 5, 1, 1)

        # save path display
        self.save_path_display = QLineEdit(self.central_widget)
        self.save_path_display.setReadOnly(True)
        self.save_path_display.setText(startrail.DEFAULT_OUT_DIR.replace("\\", "/"))
        self.central_layout.addWidget(self.save_path_display, 1, 0, 1, 5)

        # save path button 
        self.save_path_button = QPushButton(self.central_widget)
        self.save_path_button.setText("保存文件夹")
        self.central_layout.addWidget(self.save_path_button, 1, 5, 1, 1)

        # decay function label
        self.decay_function_label = QLabel(self.central_widget)
        self.decay_function_label.setText("衰减函数: ")
        self.decay_function_label.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.decay_function_label, 2, 0, 1, 1)

        # decay funciton select
        self.decay_funciton_select = QComboBox(self.central_widget)
        self.decay_funciton_select.addItems(startrail.DECAY_FUNCTIONS)
        self.central_layout.addWidget(self.decay_funciton_select, 2, 1, 1, 1)

        # decay intension label
        self.decay_intension_label = QLabel(self.central_widget)
        self.decay_intension_label.setText("衰减系数: ")
        self.decay_intension_label.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.decay_intension_label, 2, 2, 1, 1)

        # decay intension input
        self.decay_intension_input = QDoubleSpinBox(self.central_widget)
        self.decay_intension_input.setMinimum(0.001)
        self.decay_intension_input.setMaximum(1.0)
        self.decay_intension_input.setValue(0.960)
        self.decay_intension_input.setDecimals(3)
        self.decay_intension_input.setSingleStep(0.001)
        self.central_layout.addWidget(self.decay_intension_input, 2, 3, 1, 1)

        # threshold label
        self.stack_num_label = QLabel(self.central_widget)
        self.stack_num_label.setText("每帧叠加的张数: ")
        self.stack_num_label.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.stack_num_label, 2, 4, 1, 1)

        # stak num input
        self.stack_num_input = QSpinBox(self.central_widget)
        self.stack_num_input.setMinimum(1)
        self.stack_num_input.setValue(30)
        self.central_layout.addWidget(self.stack_num_input, 2, 5, 1, 1)

        # 从第几张开始计算
        self.start_label = QLabel(self.central_widget)
        self.start_label.setText("开始计算的帧数:")
        self.central_layout.addWidget(self.start_label, 3, 0, 1, 1)

        self.start_num = QSpinBox(self.central_widget)
        self.start_num.setPrefix("第")
        self.start_num.setSuffix("帧")
        self.start_num.setMinimum(1)
        self.start_num.setValue(1)
        self.central_layout.addWidget(self.start_num, 3, 1, 1, 1)

        # self.stack_num_warning = QLabel(self.central_widget)
        # self.stack_num_warning.setText("(尽量不要调整此参数, 而是使用衰减阈值来控制!)")
        # font = QFont()
        # font.setBold(True)
        # self.stack_num_warning.setFont(font)
        # self.central_layout.addWidget(self.stack_num_warning, 3, 2, 1, 3)

        # start button 
        self.start_button = QPushButton(self.central_widget)
        self.start_button.setText("Start")
        self.central_layout.addWidget(self.start_button, 3, 5, 1, 1)

        # progress bar
        self.progress_bar = QProgressBar(self.central_widget)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.progress_bar, 4, 0, 1, 6)

        # time 
        self.remain_time_label = QLabel("预计剩余时间: ")
        self.remain_time_label.setAlignment(Qt.AlignCenter)
        self.central_layout.addWidget(self.remain_time_label, 5, 0, 1, 6)

        # log display
        self.log_display = QTextEdit(self.central_widget)
        self.log_display.setReadOnly(True)
        self.central_layout.addWidget(self.log_display, 6, 0, 5, 6)
    
    def _connect(self):
        self.images_path_select_button.clicked.connect(self._select_images_path_event)
        self.save_path_button.clicked.connect(self._select_save_path_event)
        self.decay_funciton_select.currentTextChanged.connect(self._update_decay_event)
        self.decay_intension_input.valueChanged.connect(self._update_decay_event)
        # self.stack_num_input.valueChanged.connect(self._update_decay_event)
        self.start_num.valueChanged.connect(self._update_start_frame)
        self.start_button.clicked.connect(self._start_event)
        self.agent.end_signal.connect(self._update_bar)

    def _select_images_path_event(self):
        filepath = QFileDialog.getExistingDirectory(self.central_widget, dir=startrail.DESKTOP_PATH)
        if filepath != "":
            num, name1 = self.agent.get_files(filepath)
            if num != 0:
                self.input_display.setText(F"已导入[{name1}, ...]等{num}张图片")
                font = QFont()
                self.input_display.setFont(font)
                self.progress_bar.setMaximum(num)
                self.progress_bar.setValue(0)
                self.stack_num_input.setMaximum(num)
                self.start_num.setMaximum(num)
            else:
                # TODO:
                pass
        else:
            # TODO:
            pass
        
    def _select_save_path_event(self):
        filepath = QFileDialog.getExistingDirectory(self.central_widget, dir=startrail.DESKTOP_PATH)
        if filepath != "":
            new_path = self.agent.set_outdir(filepath)
            self.save_path_display.setText(new_path.replace("\\", "/"))
        else:
            # TODO:
            pass
    
    def _update_decay_event(self):
        function = self.decay_funciton_select.currentText()
        decay_intension = self.decay_intension_input.value()
        num = self.agent.get_decay_list(function, decay_intension)
        self.stack_num_input.setMaximum(num)
    
    def _update_start_frame(self):
        num = self.start_num.value()
        self.agent.set_start_frame(num)

    def _start_event(self):
        self.start_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.remain_time_label.setText("预计剩余时间:")
        num = self.stack_num_input.value()
        mythread = Thread(target=self.agent.star_trail, args=(num,), daemon=True)
        mythread.start()
        self.start_time = datetime.datetime.now()
    
    def _update_bar(self, val):
        if val == 0:
            self.start_button.setEnabled(True)
            self.remain_time_label.setText("已完成!")
        elif val == 1:
            val = self.progress_bar.value() + 1
            self.progress_bar.setValue(val)
            cost_time = (datetime.datetime.now() - self.start_time).total_seconds()
            eta_time = cost_time / val * (self.progress_bar.maximum() - val)
            eta = int(eta_time)
            hours = eta // 3600
            eta -= hours * 3600
            mins = eta // 60
            eta -= mins * 60
            secs = eta
            outstr = F"预计剩余时间: {str(hours)+' 小时' if hours != 0 else ''} {str(mins) + ' 分钟'} {str(secs)} 秒"
            self.remain_time_label.setText(outstr)

    def _write_log_info(self, text: str):
        log_cursor = self.log_display.textCursor()
        log_cursor.movePosition(QTextCursor.End)
        if text.endswith("\n"):
            self.stream_update_state = 0
        else:
            if self.stream_update_state == 1:
                log_cursor.select(QTextCursor.BlockUnderCursor)
                log_cursor.removeSelectedText()
            self.stream_update_state = 1

        log_cursor.insertText(text)
        self.log_display.setTextCursor(log_cursor)
        self.log_display.ensureCursorVisible()

class Stream(QObject):
    stream_update = Signal(str)

    def write(self, text: str):
        self.stream_update.emit(text)

if __name__ == "__main__":
    # app = QApplication(sys.argv)
    app = QApplication()
    win = MyMainWindow()
    win.show()
    app.exec()
import os
import datetime
from multiprocessing.pool import ThreadPool
import numpy as np
from PIL import Image, ImageEnhance, ImageChops, ImageStat
import natsort
from PySide6.QtCore import QObject, Signal

PATH = os.path.abspath(os.path.dirname(__file__))
USER_PATH = os.path.expanduser('~')
DESKTOP_PATH = os.path.join(USER_PATH, 'Desktop')
ROOT_PATH = os.path.dirname(PATH)
DEFAULT_OUT_DIR = os.path.join(USER_PATH, 'Desktop', 'StarTrail')
SUPPORT_IN_FORMAT = ['.jpg', '.png', '.JPG', '.PNG']
DECAY_FUNCTIONS = ['gauss', 'exp', 'linear']

class StarTrailAgent(QObject):
    end_signal = Signal(int)
    def __init__(self) -> None:
        super().__init__()
        self.files = []
        self.decay_list = []
        self.decay_funcitno = 'exp'
        self.decay_intension = 0.96
        self.out_dir = DEFAULT_OUT_DIR
        self.start_frame = 0

    def get_files(self, path: str) -> (int, str):
        files = [os.path.join(path, name) for name in os.listdir(path) if name.endswith(tuple(SUPPORT_IN_FORMAT))]
        self.files = natsort.natsorted(files, alg=natsort.PATH)
        if self.files:
            return len(self.files), os.path.basename(self.files[0])
        else:
            return 0, ""
    
    def set_outdir(self, path: str) -> str:
        new_path = os.path.join(path, "StarTrail")
        self.out_dir = new_path
        return new_path

    def get_decay_list(self, decay_function: str, decay_intension: float) -> int:
        if self.files:
            self.decay_funcitno = decay_function
            self.decay_intension = decay_intension
            if decay_intension == 1:
                self.decay_list = np.array([1.0 for x in range(len(self.files) - 1, -1, -1)])
            elif decay_intension == 0:
                return 0
            else:
                if decay_function == "exp":
                    decay_list = np.array([decay_intension ** x for x in range(len(self.files) - 1, -1, -1)])
                    self.decay_list = decay_list
                elif decay_function == "linear":
                    k = decay_intension - 1
                    decay_list = np.array([k * x + 1 for x in range(len(self.files) - 1, -1, -1)])
                    self.decay_list = decay_list[decay_list >= 0]
                elif decay_function == "gauss":
                    # c = - np.log(1 - decay_intension)
                    c = np.tan(decay_intension * np.pi / 2)
                    decay_list = np.array([np.exp(- np.power(x, 2) / (2 * np.power(c, 2))) for x in range(len(self.files) - 1, -1, -1)])
                    self.decay_list = decay_list
            print(F"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {decay_function} 衰减区间: {self.decay_list[0]:.2} ~ {self.decay_list[-1]:.2}")
            return len(self.decay_list)
        else:
            return 0
    
    def set_start_frame(self, input):
        self.start_frame = input - 1
    
    def star_trail(self, stack_num: int):
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)
        decay_list = self.decay_list[len(self.decay_list) - stack_num:]
        files = self.files[self.start_frame:]
        task_args = [(files[0 if i <= stack_num else i - stack_num: i], 
                      decay_list[- i if i < stack_num else - stack_num:]) for i in range(1, len(files) + 1)]
        with ThreadPool(8) as pool:
            ret = pool.starmap(self._unit, task_args)
        self.end_signal.emit(0)
        print(F"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 处理完成!")
    
    def _unit(self, sub_imgpath_list: list, decay_list: np.ndarray[float]):
        for i, file in enumerate(sub_imgpath_list):
            img = Image.open(file)
            brightness_enhance = ImageEnhance.Brightness(img)
            decay_img = brightness_enhance.enhance(decay_list[i])
            if i == 0:
                ret_img = decay_img
            else:
                ret_img = ImageChops.lighter(ret_img, decay_img)

        ret_stat = ImageStat.Stat(ret_img.convert("L"))
        ret_brightness = ret_stat.mean[0]
        input_stat = ImageStat.Stat(Image.open(sub_imgpath_list[-1]).convert("L"))
        input_brightness = input_stat.mean[0]
        ret_brightness_enhance = ImageEnhance.Brightness(ret_img)
        ret_img = ret_brightness_enhance.enhance(input_brightness/ret_brightness)
        ret_img.save(os.path.join(self.out_dir, f"{self.decay_funcitno}_{self.decay_intension:.2}_{os.path.basename(sub_imgpath_list[-1])}"))
        self.end_signal.emit(1)
        print(F"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {len(sub_imgpath_list)} {len(decay_list)} 张最大值堆栈 {os.path.basename(sub_imgpath_list[-1])} ok!\n", end="")

    # 该方案会吃满内存 无法有效使用
    def _unit2(self, sub_imgpath_list: list, decay_list: np.ndarray[float]):
        num = len(sub_imgpath_list)
        len_decay = len(decay_list)
        img_list = []
        img_L_list = []
        for i, file in enumerate(sub_imgpath_list):
            decay = decay_list[len_decay - num + i]
            img = Image.open(file)
            img_L = img.convert("L")
            img = (np.array(img) * decay).astype("uint8")
            img_L = (np.array(img) * decay).astype("uint8")
            img_list.append(img)
            img_L_list.append(img_L)
        img_all = np.array(img_list)
        img_L_all = np.array(img_L_list)
        id_layer = img_L_all.argmax(axis=0)
        id_y = np.array([list(range(id_layer.shape[1])) for x in range(id_layer.shape[0])])
        id_x = np.array([list(range(id_layer.shape[0])) for x in range(id_layer.shape[1])]).T
        ret_img = img_all[id_layer, id_y, id_x]
        ret_img = Image.fromarray(ret_img)

        ret_stat = ImageStat.Stat(ret_img.convert("L"))
        ret_brightness = ret_stat.mean[0]
        input_stat = ImageStat.Stat(Image.open(sub_imgpath_list[-1]).convert("L"))
        input_brightness = input_stat.mean[0]
        ret_brightness_enhance = ImageEnhance.Brightness(ret_img)
        ret_img = ret_brightness_enhance.enhance(input_brightness/ret_brightness)
        ret_img.save(os.path.join(self.out_dir, f"{self.decay_funcitno}_{self.decay_intension:.2}_{self.decay_threshold:.2}_{os.path.basename(sub_imgpath_list[-1])}"))
        self.end_signal.emit(1)
        print(F"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {num} 张最大值堆栈 {os.path.basename(sub_imgpath_list[-1])} ok!\n", end="")
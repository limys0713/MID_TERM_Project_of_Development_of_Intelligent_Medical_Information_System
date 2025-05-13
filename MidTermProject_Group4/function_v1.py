import RPi.GPIO as GPIO
import time
import threading
import Adafruit_SSD1306
from PIL import Image, ImageDraw, ImageFont
import base64
import requests
import socket
import struct
import pyaudio
import wave
import subprocess
import re
import random

# GPIO 基本設定
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO_TRIGGER = 23
GPIO_ECHO = 24

GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)

STEPPER_PINS = [17, 18, 27, 22]
SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

# 啟動馬達（非阻塞）
class MotorTimer(threading.Thread):
    def __init__(self, seconds_per_turn=5):
        super().__init__()
        self.seconds_per_turn = seconds_per_turn
        self.done = False

    def run(self):
        STEPS_PER_REV = 64 * 64  # 4096 steps
        wait_per_step = self.seconds_per_turn / STEPS_PER_REV
        GPIO.setmode(GPIO.BCM)
        for pin in STEPPER_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)

        seq_index = 0
        for step in range(STEPS_PER_REV):
            for pin in range(4):
                GPIO.output(STEPPER_PINS[pin], SEQUENCE[seq_index][pin])
            seq_index = (seq_index + 1) % len(SEQUENCE)
            time.sleep(wait_per_step)

        self.done = True
        for pin in STEPPER_PINS:
            GPIO.output(pin, GPIO.LOW)

# OLED 顯示文字
def display_text(text, *args):
    disp = Adafruit_SSD1306.SSD1306_128_64(rst=0)
    disp.begin()
    disp.clear()
    disp.display()

    width = disp.width
    height = disp.height

    image = Image.new('1', (width, height))
    draw = ImageDraw.Draw(image)

    # 支援中文的字型（請確認字型檔與.py在同一資料夾，或使用完整路徑）
    try:
        if len(args) < 2:
            FONT_SIZE = 15
        elif len(args) == 2:
            FONT_SIZE = 10
        else:
            FONT_SIZE = 8

        font = ImageFont.truetype("ARIALUNI.TTF", FONT_SIZE)  # or "./fonts/ARIALUNI.TTF"
    except Exception as e:
        print("字型載入失敗：", e)
        return

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((0, 0), text, font=font, fill=255)

    for i, item in enumerate(args):
        draw.text((0, (i + 1) * FONT_SIZE - 1), str(item), font=font, fill=255)

    disp.image(image)
    disp.display()
    time.sleep(0.1)


# 量測距離
def distance():
    GPIO.output(GPIO_TRIGGER, True)
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    start_time = time.time()
    stop_time = time.time()

    while GPIO.input(GPIO_ECHO) == 0:
        start_time = time.time()

    while GPIO.input(GPIO_ECHO) == 1:
        stop_time = time.time()

    time_elapsed = stop_time - start_time
    dist = (time_elapsed * 34300) / 2
    return dist

# TTS 客戶端
class TTSClient:
    def __init__(self):
        self.__host = "140.116.245.157"
        self.__token = "mi2stts"
        self.__port = None
        self.__model = None
        self.__language = None

    def set_language(self, language: str, model: str):
        self.__language = language.lower()
        if self.__language == "hakka":
            self.__port = 10010
            self.__model = "hedusi"
        elif self.__language == "taiwanese":
            self.__port = 10012
            self.__model = model if model else "M12"
        elif self.__language == "chinese":
            self.__port = 10015
            self.__model = model if model else "M60"
        else:
            raise ValueError("language 必須是 chinese / taiwanese / hakka")

    def askForService(self, text: str):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.__host, self.__port))
            msg = bytes(self.__token + "@@@" + text + "@@@" + self.__model + "@@@" + self.__language, "utf-8")
            msg = struct.pack(">I", len(msg)) + msg
            sock.sendall(msg)
            with open("output.wav", "wb") as f:
                while True:
                    l = sock.recv(8192)
                    if not l:
                        break
                    f.write(l)
            subprocess.run(["aplay", "output.wav"])
        except Exception as e:
            print(e)
        finally:
            sock.close()

# 錄音
class Recorder:
    def __init__(self):
        self.recording = False

    def start_recording(self):
        sample_format = pyaudio.paInt16
        channels = 1
        sample_rate = 16000
        chunk = 1024
        self.output_file = "recording.wav"

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(format=sample_format, channels=channels, rate=sample_rate, input=True, frames_per_buffer=chunk)
        self.frames = []
        self.recording = True
        print("開始錄音...再按 Enter 停止")

        while self.recording:
            data = self.stream.read(chunk)
            self.frames.append(data)

        self.stop_recording()

    def stop_recording(self):
        print("錄音結束")
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

        with wave.open(self.output_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)
            wf.writeframes(b''.join(self.frames))

    def record(self):
        record_thread = threading.Thread(target=self.start_recording)
        record_thread.start()
        input()  # Enter 停止
        self.recording = False
        record_thread.join()

# 語音辨識
def recognize_audio(file_path):
    url = 'http://140.116.245.149:5002/proxy'
    with open(file_path, 'rb') as file:
        raw_audio = file.read()
        audio_data = base64.b64encode(raw_audio)
        data = {
            'lang': 'STT for course',
            'token': '2025@ME@asr',
            'audio': audio_data.decode()
        }
        response = requests.post(url, data=data)
    if response.status_code == 200:
        result = response.json()
        print("辨識結果：", result['sentence'])
        return result['sentence']
    else:
        print("辨識失敗：", response.text)
        return ""

def parse_questions(text):
    questions = []
    blocks = re.split(r"\n(?=第[一二三四五六七八九十]+題：)", text.strip())

    for block in blocks:
        try:
            q_match = re.search(r"(第[一二三四五六七八九十]+題：.*)", block)
            a_match = re.search(r"選項一：\s*(.*)", block)
            b_match = re.search(r"選項二：\s*(.*)", block)
            c_match = re.search(r"選項三：\s*(.*)", block)
            d_match = re.search(r"選項四：\s*(.*)", block)
            ans_match = re.search(r"正解：([ABCD])", block)

            if all([q_match, a_match, b_match, c_match, d_match, ans_match]):
                questions.append({
                    "question": q_match.group(1).strip(),
                    "options": {
                        "A": a_match.group(1).strip(),
                        "B": b_match.group(1).strip(),
                        "C": c_match.group(1).strip(),
                        "D": d_match.group(1).strip()
                    },
                    "answer": ans_match.group(1).strip()  # A~D
                })
        except Exception as e:
            print(f"解析錯誤：{e}")
            continue

    return questions


# API取得文章與問題
def api():
    api_key = "86bb4c18eb682dbbc50006bb75183b73df3ded0b46f12e739192a04aeda3fe22"
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {api_key}"
    }

    # 三篇文章的內容
    articles = [
        # 文章1：豆干
        """
        標題：豆干該買「黃or白」？營養師親揭玄機　吃錯恐致癌、傷生育。
        豆干是台灣料理的靈魂食材之一，但挑錯食用恐有致癌風險。
        「豆干」是許多台灣料理不可或缺的靈魂食材，但營養師夏子雯卻發文指出，
        市場上常見的「黃豆干」，其實是從「白豆干」添加合法食用色素來提升賣相，
        假設有不肖廠商使用非法工業用染料的話，甚至會導致豆干具有致癌性，
        恐引發神經與生殖發育問題。
        她建議民眾選擇來源可靠、標示清楚的豆干品牌，減少食安風險。
        """,

        # 文章2：脂肪肝與肝癌
        """
        根據衛福部統計，肝癌長年位居台灣十大癌症死因之列，2021年共奪走7,781條寶貴生命，僅次於肺癌，成為第二大癌症死因。
        醫師指出，肝癌的發展往往並非突然，而是經歷「肝炎 → 肝硬化 → 肝癌」的漸進式過程。
        「脂肪肝」已悄悄成為肝癌的重要前期因子，卻經常被忽視。
        脂肪肝與營養失衡、高油高糖飲食、飲酒過量、缺乏運動、肥胖密切相關。
        醫師建議應從減重、運動與低脂飲食介入，必要時考慮藥物。
        有肝病家族史、肥胖或糖尿病者應定期做肝功能檢查與超音波。
        """,

        # 文章3：蔗糖素與代謝健康
        """
        現代人流行無糖飲食，代糖如蔗糖素被視為替代選擇。
        然而研究發現，蔗糖素可能降低胰島素敏感性、改變腸道菌相，增加代謝疾病風險。
        吳映蓉指出，連續兩週喝蔗糖素會讓健康成人的胰島素敏感度下降約18%。
        也有研究指出，蔗糖素加劇高脂飲食下的胰島素阻抗。
        腸道菌相改變會造成慢性低度發炎，使血糖調節更困難。
        營養師提醒：零糖 ≠ 零風險。
        """, 

        # 文章4
        """
        睡前滑手機成失眠元兇？研究：藍光干擾褪黑激素分泌。
        不少人習慣睡前滑手機放鬆，但醫師提醒，手機螢幕的藍光可能導致睡眠障礙。
        研究發現，藍光會抑制褪黑激素分泌，讓大腦誤以為還在白天，進而影響入睡時間與睡眠品質。
        長期下來可能導致失眠、焦慮與白天嗜睡等問題。
        醫師建議睡前一小時盡量遠離螢幕，或開啟夜間模式、使用藍光濾鏡功能，有助於維持健康睡眠節奏。
        """,

        # 文章5
        """
        久坐像慢性毒藥？醫警告：每天坐超過8小時，心臟恐不堪負荷。
        現代人工作型態改變，久坐已成常態，但醫師警告，長時間缺乏活動會加重心血管負擔。
        研究指出，每天坐超過8小時、且缺乏運動者，罹患心血管疾病與早逝風險大幅上升。
        久坐會降低下肢血液循環，導致靜脈栓塞與血壓上升。
        醫師建議每工作50分鐘應起身活動5到10分鐘，並養成規律運動習慣，以減少代謝與心臟病風險。
        """,

        # 文章6
        """
        你今天喝夠水了嗎？醫：水分攝取不足恐傷腎、易結石。
        人體超過七成是水分，但許多人日常喝水量不足，對腎臟恐造成潛在傷害。
        醫師指出，長期水分攝取不足，會使尿液濃縮、結晶物質增加，導致腎結石與感染風險升高。
        尤其天氣炎熱或大量流汗時，更應補充水分以維持代謝與電解質平衡。
        一般成人每日建議飲水量為2000c.c.左右，可依個人體重與活動量調整。
        """
    ]

    # 隨機選一篇文章
    article_text = random.choice(articles)

    prompt = f"""
    你是一個專業的閱讀理解老師。

    請閱讀下面這篇文章，並根據內容出3個中文的選擇題，每題包含：
    - 題幹（用「第一題」「第二題」開頭）
    - 四個選項（選項一～選項四）
    - 正確答案（用 A/B/C/D 表示）

    請嚴格按照以下格式輸出：
    第一題：......
    選項一：......
    選項二：......
    選項三：......
    選項四：......
    正解：A

    （不要加解釋或括號，只要乾淨格式）

    文章內容：
    {article_text}
    """


    data = {
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
        "messages": [
            {"role": "system", "content": "你是一個閱讀理解題目的生成器，專門從文章中提問問題。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 500
    }

    try:
        response = requests.post(url=url, json=data, headers=headers)
        if response.status_code == 200:
            result = response.json()
            questions_text = result["choices"][0]["message"]["content"]
            questions = parse_questions(questions_text)
            return article_text, questions
        else:
            print(f"產生失敗，狀態碼：{response.status_code}")
            print(response.text)
            return article_text, []
    except Exception as e:
        print(f"發生例外錯誤：{e}")
        return article_text, []


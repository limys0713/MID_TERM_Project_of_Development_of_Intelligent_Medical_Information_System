import function_v1
import time

def distance_to_choice(dist_cm):
    """根據距離判斷選項"""
    if dist_cm < 8:
        return '選項一'
    elif dist_cm < 13.5:
        return '選項二'
    elif dist_cm < 19:
        return '選項三'
    elif dist_cm < 24.5:
        return '選項四'
    else:
        return '選項四'

if __name__ == "__main__":
    # 載入文章與問題
    article_text, questions = function_v1.api()

    #print(questions)

    # label 對照表
    label_to_text = {
        "A": "選項一",
        "B": "選項二",
        "C": "選項三",
        "D": "選項四"
    }

    # 初始化 TTS 客戶端
    tts_client = function_v1.TTSClient()
    tts_client.set_language(language="chinese", model="M60")

    # 播放整篇文章
    tts_client.askForService("請聽文章")
    print(f"文章：\n{article_text}")
    # 可選擇是否播文章內容本身
    tts_client.askForService(article_text)
    tts_client.askForService("文章已結束，準備好回答問題了嗎？請說「準備好了」或「開始」")

    # 開始錄音等待使用者回覆
    recorder = function_v1.Recorder()
    recorder.record()

    # 語音辨識
    reply = function_v1.recognize_audio("recording.wav").strip()

    if "準備好了" in reply or "開始" in reply:
        tts_client.askForService("好的，我們開始問問題囉！")

        timer_count = 10
        for q in questions:
            # 播放題目
            tts_client.askForService(q["question"])

            # 播放選項（key: A~D）
            for label, content in q["options"].items():
                spoken = label_to_text[label]
                tts_client.askForService(f"{spoken}：{content}")
                time.sleep(0.1)

            tts_client.askForService("準備好作答了嗎？馬達轉一圈的時間內可以自由選擇喔！")

            # 啟動馬達計時
            motor_timer = function_v1.MotorTimer(seconds_per_turn=timer_count)
            motor_timer.start()

            last_choice = '選項四'  # 預設
            while not motor_timer.done:
                try:
                    dist = function_v1.distance()
                    choice = distance_to_choice(dist)

                    if choice != last_choice:
                        function_v1.display_text(f"距離: {dist:.1f}cm", f"選擇: {choice}")
                        last_choice = choice

                    time.sleep(0.1)
                except Exception as e:
                    print(f"測距失敗：{e}")
                    continue

            print(f"最終選擇: {last_choice}")
            function_v1.display_text("作答結束", f"你選: {last_choice}")

            # 對照正解（answer 是 A/B/C/D）
            correct_text = label_to_text[q["answer"]]
            
            # 顯示在 OLED 上
            function_v1.display_text("結果：", f"你選：{last_choice}", f"正解：{correct_text}")

            if last_choice == correct_text:
                tts_client.askForService("回答正確！恭喜你！")
            else:
                tts_client.askForService(f"答錯了喔！正確答案是 {correct_text}。")

            time.sleep(0.5)
            timer_count -= 3

        tts_client.askForService("問答結束，謝謝您的參與。")
    else:
        tts_client.askForService("沒有偵測到開始指令，結束程式。")



import requests

api_key = ""

# API endpoint
url = "https://api.together.xyz/v1/chat/completions"

# Header
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "authorization": f"Bearer {api_key}"
}


input = "豆干該買「黃or白」？營養師親揭玄機　吃錯恐致癌、傷生育。豆干是台灣料理的靈魂食材之一，但挑錯食用恐有致癌風險。豆干是台灣料理的靈魂食材之一，但挑錯食用恐有致癌風險。「豆干」是許多台灣料理不可或缺的靈魂食材，但營養師夏子雯卻發文指出，市場上常見的「黃豆干」，其實是從「白豆干」添加合法食用色素來提升賣相，假設有不肖廠商使用非法工業用染料的話，甚至會導致豆干具有致癌性，恐引發神經與生殖發育問題。夏子雯日前在臉書粉專「夏子雯-貼近你生活的營養師」發文指出，豆干屬於一種低度加工的豆製品，並經由加壓、脫水、加入凝固劑製成，並不算是過度加工食物，因此是一種很良好的蛋白質來源。夏子雯表示，不論是在逛超市或傳統市場，市面上常見的豆干都是「黃豆干」而非「白豆干」，但過去為了延長白豆干的保存期限，經常會用「糖烏」滷製成黃豆干，現在則多由添加食用色素（如黃色4號、5號）來提升賣相。夏子雯補充，儘管黃豆干正常情況下是良好蛋白質來源，但若有不肖廠商使用皂黃、二甲基黃等非法工業用染料，即會產生致癌性，恐影響神經與生殖發育。因此，她也建議民眾們在選擇豆製品時，務必優先選購包裝清楚，且來源可靠的品牌、店家，降低食安風險。事實上，過去食藥署也曾指出，豆干原色應為偏白色，但因為業者會使用合法著色劑，像是焦糖色素、食用黃色4號或5號色素，故市售豆干才會呈現黃或棕褐色。食藥署提醒，購買豆干製品時應確認包裝完整性與是否有明確標示，至於選購散裝豆干則要留意外觀與氣味，方可確保食安無虞。"

prompt = f"""
你是一個專業的閱讀理解老師。

請閱讀下面這篇文章，並根據文章內容出5個中文的閱讀理解問題。

問題要清楚、簡潔，而且必須只根據文章中的資訊出題。

文章內容：
{input}
"""

# Data that needed to be sent
data = {
    "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",  # Free model (good quality)
    "messages": [
        {"role": "system", "content": "你是一個閱讀理解題目的生成器，專門從文章中提問問題。"},
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.5,   # Balanced creativity
    "max_tokens": 500     # How long the response can be (adjust if your article is very long)
}

# Send the request
response = requests.post(url=url, json=data, headers=headers)

# Handle the response
if response.status_code == 200:
    output = response.json()
    questions = output['choices'][0]['message']['content']
    print("問題如下：\n")
    print(questions)
else:
    print("Error: ", response.status_code)
    print(response.text)

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import random

# 載入資料
file_path = "健保特約醫事機構-地區醫院_ 健保特約醫事機構_地區醫院.csv"
df = pd.read_csv(file_path)

# 建立 Google Maps URL
df["URL"] = "https://www.google.com/maps/place?q=" + df["地址"].str.replace(" ", "+")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 爬取座標
for i, row in df.iterrows():
    try:
        url = row["URL"]
        # 您可以增加延遲時間以減少被阻擋的風險
        time.sleep(random.randint(10, 20))
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.prettify()
        initial_pos = text.find(";window.APP_INITIALIZATION_STATE")
        data = text[initial_pos + 36:initial_pos + 85]
        line = tuple(data.split(','))
        num1 = line[1]
        num2 = line[2]
        df.at[i, "latitude"] = num1
        df.at[i, "longitude"] = num2
    except:
        df.at[i, "latitude"] = None
        df.at[i, "longitude"] = None

# 儲存結果
df.to_csv("健保特約醫事機構-地區醫院_座標結果.csv", index=False)

import os
import json
from datetime import datetime
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage
from math import radians, sin, cos, sqrt, atan2

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

# 從 abc_point.json 讀取資料
with open('abc_point.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

def safe_float_convert(value, default=0.0):
    try:
        return float(value)
    except ValueError:
        return default

PLACES = [
    {
        'name': item['機構名稱'],
        'time': item['最後異動時間'],
        'lat': safe_float_convert(item['緯度']),
        'lon': safe_float_convert(item['經度'])
    } for item in data
]

def get_distance(place, lat, lon):
    R = 6371  # 地球的半徑（公里）
    
    lat1 = radians(place["lat"])
    lon1 = radians(place["lon"])
    lat2 = radians(lat)
    lon2 = radians(lon)
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    distance = R * c
    return distance

@app.route("/", methods=["GET", "POST"])
def callback():
    if request.method == "GET":
        return "Hello Heroku"
    if request.method == "POST":
        signature = request.headers["X-Line-Signature"]
        body = request.get_data(as_text=True)

        try:
            handler.handle(body, signature)
        except InvalidSignatureError:
            abort(400)

        return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    get_message = event.message.text
    reply = TextSendMessage(text=f"{get_message}132")
    line_bot_api.reply_message(event.reply_token, reply)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    user_lat = event.message.latitude
    user_lon = event.message.longitude

    distances = [(place, get_distance(place, user_lat, user_lon)) for place in PLACES]
    closest_places = sorted(distances, key=lambda x: x[1])[:3]

    reply_text = "距離您最近的三個據點是：\n"
    for place, distance in closest_places:
        reply_text += f"{place['name']}，距離：{distance:.2f}公里\n資料更新時間：{place['time']}\n"

    reply = TextSendMessage(text=reply_text)
    line_bot_api.reply_message(event.reply_token, reply)

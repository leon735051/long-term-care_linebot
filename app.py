import os
import json

from datetime import datetime

from flask import Flask, abort, request

# https://github.com/line/line-bot-sdk-python
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage

app = Flask(__name__)

line_bot_api = LineBotApi(os.environ.get("CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("CHANNEL_SECRET"))

# 從 abc_point.json 讀取資料
with open('abc_point.json', 'r', encoding='utf-8') as file:
    data = json.load(file)

PLACES = [
    {
        'name': item['機構名稱'],
        'lat': item['緯度'],
        'lon': item['經度']
    } for item in data
]

from math import sqrt

def get_distance(place, lat, lon):
    return sqrt((place["lat"] - lat)**2 + (place["lon"] - lon)**2)

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
        reply_text += f"{place['name']}，距離：{distance:.2f}公里\n"

    reply = TextSendMessage(text=reply_text)
    line_bot_api.reply_message(event.reply_token, reply)

import os
import json
from datetime import datetime
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage, FlexSendMessage, BubbleContainer, CarouselContainer, ButtonComponent, URIAction
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

unique_places = {}
for item in data:
    name = item['機構名稱']
    address = item['地址全址']
    phone = item['機構電話']
    lat = safe_float_convert(item['緯度'])
    lon = safe_float_convert(item['經度'])
    unique_places[name] = {
        'name': name, 
        'lat': lat, 
        'lon': lon, 
        'address': address,
        'phone': phone
    }

PLACES = list(unique_places.values())


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

    bubbles = []

    for place, distance in closest_places:
        map_url = f"https://www.openstreetmap.org/?mlat={place['lat']}&mlon={place['lon']}#map=16/{place['lat']}/{place['lon']}"
        
        bubble = BubbleContainer(
            body={
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": place['name'],
                        "weight": "bold",
                        "size": "xl"
                    },
                    {
                        "type": "text",
                        "text": place['address'],
                        "wrap": True,
                        "color": "#666666",
                        "size": "sm"
                    },
                    {
                        "type": "text",
                        "text": f"電話: {place['phone']}",
                        "wrap": True,
                        "color": "#666666",
                        "size": "sm"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "距離",
                                        "color": "#aaaaaa",
                                        "size": "sm",
                                        "flex": 1
                                    },
                                    {
                                        "type": "text",
                                        "text": f"{distance:.2f} 公里",
                                        "wrap": True,
                                        "color": "#666666",
                                        "size": "sm",
                                        "flex": 5
                                    }
                                ]
                            },
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#0000FF",  # 設定為藍色
                                "height": "sm",
                                "action": {
                                    "type": "uri",
                                    "label": "查看地圖",
                                    "uri": map_url
                                }
                            }
                        ]
                    }
                ]
            }
        )
        bubbles.append(bubble)



    carousel = CarouselContainer(contents=bubbles)

    flex_message = FlexSendMessage(
        alt_text="距離您最近的三個據點",
        contents=carousel
    )
    
    line_bot_api.reply_message(event.reply_token, flex_message)

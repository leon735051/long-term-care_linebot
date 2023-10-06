import os
import json
from datetime import datetime
from flask import Flask, abort, request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, LocationMessage, FlexSendMessage, BubbleContainer, CarouselContainer, ButtonComponent, URIAction, QuickReply, QuickReplyButton, MessageAction
from math import radians, sin, cos, sqrt, atan2
import csv
# 全局變量，用來保存用戶狀態
user_states = {}

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

clinic_data = []
with open('健保特約醫事機構-診所_座標結果.csv', mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header row
    for row in reader:
        code, name, type_, phone, address, _, _, _, _, _, _, _, _, _, url, lon, lat = row
        clinic_data.append({
            'name': name, 
            'lat': safe_float_convert(lat), 
            'lon': safe_float_convert(lon), 
            'address': address,
            'phone': phone,
            'url': url
        })
        
district_hospital_data = []
with open('健保特約醫事機構-地區醫院_座標結果.csv', mode='r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header row
    for row in reader:
        code, name, type_, phone, address, _, _, _, _, _, _, _, _, _, url, lon, lat = row
        district_hospital_data.append({
            'name': name, 
            'lat': safe_float_convert(lat), 
            'lon': safe_float_convert(lon), 
            'address': address,
            'phone': phone,
            'url': url
        })

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
    user_id = event.source.user_id
    get_message = event.message.text

    # 當用戶輸入"查詢"時
    if get_message == "查詢":
        items = [
            QuickReplyButton(action=MessageAction(label="ABC據點", text="ABC據點")),
            QuickReplyButton(action=MessageAction(label="醫院", text="醫院")),
            QuickReplyButton(action=MessageAction(label="診所", text="診所"))
        ]
        reply = TextSendMessage(text="請選擇查詢類型", quick_reply=QuickReply(items=items))
    elif get_message in ["ABC據點", "醫院", "診所"]:
        user_states[user_id] = get_message
        reply = TextSendMessage(text="請回傳您的位資訊")
    else:
        reply = TextSendMessage(text=f"請輸入查詢")

    line_bot_api.reply_message(event.reply_token, reply)

@handler.add(MessageEvent, message=LocationMessage)
def handle_location(event):
    user_id = event.source.user_id
    if user_id not in user_states:
        # 預設回應
        reply = TextSendMessage(text="請先選擇查詢類型")
        line_bot_api.reply_message(event.reply_token, reply)
        return
    user_lat = event.message.latitude
    user_lon = event.message.longitude
    distances = []
    closest_places = []
    bubbles = []
    if user_states[user_id] == "ABC據點":
        distances = [(place, get_distance(place, user_lat, user_lon)) for place in PLACES]
        closest_places = sorted(distances, key=lambda x: x[1])[:3]

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
                            "size": "lg"
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
                                            "text": f"距離你的位置{distance:.2f} 公里",
                                            "wrap": True,
                                            "color": "#0000FF",
                                            "size": "sm",
                                            "flex": 5,
                                            "align": "center"    # 水平居中
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
        pass
    elif user_states[user_id] == "醫院":
        distances = [(district, get_distance(district, user_lat, user_lon)) for district in district_hospital_data]
        closest_places = sorted(distances, key=lambda x: x[1])[:3]
        for district, distance in closest_places:
            map_url = f"https://www.openstreetmap.org/?mlat={district['lat']}&mlon={district['lon']}#map=16/{district['lat']}/{district['lon']}"
            
            bubble = BubbleContainer(
                body={
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": district['name'],
                            "weight": "bold",
                            "size": "lg"
                        },
                        {
                            "type": "text",
                            "text": district['address'],
                            "wrap": True,
                            "color": "#666666",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"電話: {district['phone']}",
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
                                            "text": f"距離你的位置{distance:.2f} 公里",
                                            "wrap": True,
                                            "color": "#0000FF",
                                            "size": "sm",
                                            "flex": 5,
                                            "align": "center"    # 水平居中
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
            alt_text="距離您最近的三個醫院",
            contents=carousel
        )
        
        line_bot_api.reply_message(event.reply_token, flex_message)
    elif user_states[user_id] == "診所":
        distances = [(clinic, get_distance(clinic, user_lat, user_lon)) for clinic in clinic_data]
        closest_places = sorted(distances, key=lambda x: x[1])[:3]

        for clinic, distance in closest_places:
            map_url = f"https://www.openstreetmap.org/?mlat={clinic['lat']}&mlon={clinic['lon']}#map=16/{clinic['lat']}/{clinic['lon']}"
            
            bubble = BubbleContainer(
                body={
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": clinic['name'],
                            "weight": "bold",
                            "size": "lg"
                        },
                        {
                            "type": "text",
                            "text": clinic['address'],
                            "wrap": True,
                            "color": "#666666",
                            "size": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"電話: {clinic['phone']}",
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
                                            "text": f"距離你的位置{distance:.2f} 公里",
                                            "wrap": True,
                                            "color": "#0000FF",
                                            "size": "sm",
                                            "flex": 5,
                                            "align": "center"    # 水平居中
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
            alt_text="距離您最近的三個診所",
            contents=carousel
        )
        
        line_bot_api.reply_message(event.reply_token, flex_message)

    del user_states[user_id]  # 處理完畢後，清除用戶狀態


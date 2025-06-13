import os
import requests # HTTPリクエスト用
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

# データベース関連
import database
import models
from sqlalchemy.orm import Session

from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

# .envファイルから環境変数を読み込む
load_dotenv()

# データベースにテーブルが存在しない場合、自動的に作成
models.Base.metadata.create_all(bind=database.engine)

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# 環境変数から設定情報を取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')

# LINE Messaging APIの設定
configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 指定された都市の天気の情報を取得する
def get_weather_from_api(city_name: str) -> str:
    if not city_name:
        return "都市名が入力されていません。"
    
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q' : city_name,
        'appid' : OPENWEATHERMAP_API_KEY,
        'units' : 'metric', # 摂氏で取得
        'lang' : 'ja'       # 結果を日本語で
    }

    try:
        response = requests.get(base_url,params=params)
        response.raise_for_status() # ステータスコードが200番台以外ならHTTPErrorを発生させる
        data = response.json()

        # APIからのレスポンスでエラーコードが返ってきた場合の処理
        if data.get("cod") != 200: # 成功時はcodは200になる
            error_message = data.get("message", "天気情報を取得できませんでした。")
            return f"「{city_name}」の天気情報取得エラー:{error_message}都市名を確認してください。"
        
        # 天気情報を抽出
        weather_description = data['weather'][0]['description']
        temp = data['main']['temp']
        temp_min = data['main']['temp_min']
        temp_max = data['main']['temp_max']
        humidity = data['main']['humidity']

        # ユーザへの返信メッセージ
        reply_text = (
            f"【{city_name}の現在の天気】\n"
            f"天気: {weather_description}\n"
            f"気温: {temp}°C\n"
            # f"最低気温: {temp_min}°C\n"
            # f"最高気温: {temp_max}°C\n"
            f"湿度: {humidity}%"
        )
        return reply_text
    
    except requests.exceptions.HTTPError as http_error:
        # HTTPエラー
        if response.status_code == 401:
            return "天気APIの認証に失敗しました。APIキーが正しいか確認してください。"
        elif response.status_code == 404:
            return f"「{city_name}」の天気情報が見つかりませんでした。都市名が正しいか確認してください。"
        else:
            return f"天気情報の取得中にHTTPエラーが発生しました:{http_error}"
    except requests.exceptions.RequestException as req_err:
        # ネットワークの接続エラー
        return f"天気APIへの接続中にエラーが発生しました: {req_err}"
    except KeyError:
        # APIレスポンスの構造が予想したものと異なる場合
        return f"「{city_name}」の天気情報を解析できませんでした。APIからのデータ形式が正しくない場合があります。"
    except Exception as e:
        # その他の予期せぬエラー
        print(f"予期せぬエラーが発生しました: {e}")
        return "天気情報の取得中に予期せぬエラーが発生しました。"
    
@app.post("/callback") # LINEからのWebhookはこのURLにPOSTリクエストで届く
async def callback(request: Request):
    #LINEからのリクエスト署名を検証
    signature = request.headers.get('X-Line-Signature')
    if signature is None:
        raise HTTPException(status_code=400, detail="X-Line-Signature header not found")
        
    #リクエストボディを取得
    body = await request.body()
    body_str = body.decode('utf-8')

    try:
        # WebhookHandlerで署名検証とイベント処理
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        print("署名が無効です。LINE Channel Secretを確認してください。")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        print(f"Webhook処理中にエラー: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {e}")
        
    return 'OK' # LINEプラットフォームに正常処理を伝える

@handler.add(MessageEvent, message=TextMessageContent) # テキストメッセージをを受信したときの処理
def handle_message(event):
    user_message = event.message.text # ユーザが送信したメッセージ(都市名)
    line_user_id = event.source.user_id # ユーザID
    reply_text = ""
    print(f"受信メッセージ: {user_message}")

    # 特定のメッセージに返信
    #キーワードと返信を辞書で定義
    keyword_responses = {
        "ありがとう": "どういたしまして！お役に立てて良かったです！",
        "こんにちは": "こんにちは！都市名を入力すると、天気を調べますよ。",
        "おはよう": "おはようございます！良い一日を！"
    }

    # データベースセッションを開始
    db = database.SessionLocal()
    try:
        # 登録で始まるメッセージか確認
        if user_message.startswith("登録"):
            # 登録以降の文字を都市名として取得
            city = user_message.split(" ", 1)[1]
            # city = user_message.split("　", 1)[1]
            if not city:
                reply_text = "都市名が入力されていません。「登録 東京」のように入力してください"
            else:
                # データベースからユーザを検索
                db_user = db.query(models.User).filter(models.User.use_id == line_user_id).first()
                if db_user:
                    # すでに登録済みなら都市名を更新
                    db_user.city = city
                    reply_text = f"都市名を「{city}」に更新しました。"
                else:
                    # 新規ユーザなら新規登録
                    new_user = models.User(user_id=line_user_id, city=city)
                    db.add(new_user)
                    reply_text = f"通知都市を「{city}に登録しました。毎朝通知します！」"

                db.commit()
        elif user_message in keyword_responses:
            reply_text = keyword_responses[user_message]  
        else:
            # 天気情報を取得
            reply_text = get_weather_from_api(user_message)

    # データベースセッションを閉じる
    finally:
        db.close()

    # ユーザに天気情報を返信
    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
        print(f"返信メッセージ: {reply_text}")
    except Exception as e:
        print(f"LINEへの返信中にエラー: {e}")

# uvicornサーバーを起動するための設定(Renderで実行する際に必要)
if __name__ == "__main__":
    # RenderはPOST環境変数を自動で設定します。ローカルではデフォルト8000番
    port = int(os.getenv("PORT", 8000))
    # Render上で実行する場合、ホストは"0.0.0.0"にする
    uvicorn.run(app, host="0.0.0.0", port=port)
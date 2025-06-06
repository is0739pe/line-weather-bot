import os
import requests # HTTPリクエスト用
from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import Configuration,ApiClient,MessagingApi,ReplyMessageRequest,TextMessageContent

# .envファイルから環境変数を読み込む
load_dotenv()

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# 環境変数から設定情報を取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
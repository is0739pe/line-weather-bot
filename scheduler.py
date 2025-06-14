import os
from dotenv import load_dotenv

# 必要な部品をインポートする
import database
import models
from main import get_weather_from_api # 天気取得関数を借りる
from linebot.v3.messaging import(
    Configuration,
    ApiClient,
    MessagingApi,
    TextMessage,
    PushMessageRequest, # Pushメッセージ用のリクエスト
)

def send_daily_weather_forecast():
    # データベースに登録されているユーザ全員に通知を送る
    print("=== 天気通知バッチ処理開始 ===")

    # 環境変数を読み込む
    load_dotenv()

    # 環境変数を取得
    LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

    # LINE MessagingApiの準備
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    line_bot_api = MessagingApi(ApiClient(configuration))

    # データベースセッションを開始
    db = database.SessionLocal()
    try:
        # 全ユーザを取得
        all_users = db.query(models.User).all()

        if not all_users:
            print("通知対象のユーザがいません")
            return

        print(f"{len(all_users)}人のユーザに通知を送信します")

        # 各ユーザに順番に通知を送る
        for user in all_users:
            try:
                # ユーザが設定した都市の天気情報を取得
                weather_report = get_weather_from_api(user.city)

                # 送信するメッセージを作成
                message_text = f"【{user.city}の今日の天気】\n{weather_report}"

                # Pushメッセージを送信
                line_bot_api.push_message(
                    PushMessageRequest(
                        to = user.user_id,
                        messages=[TextMessage(text=message_text)]
                    )
                )
                print(f"{user.user_id}へ「{user.city}」の天気を送信しました")
            except Exception as e:
                # エラーがおきても他のユーザの処理を続行
                print(f"エラー: {user.user_id} への通知送信に失敗しました。詳細: {e}")

    finally:
        db.close()

    print("===== 天気通知バッチ処理終了 =====")

# このファイルが直接実行されたときに、上記の関数を呼び出す
if __name__ == "__main__":
    send_daily_weather_forecast()

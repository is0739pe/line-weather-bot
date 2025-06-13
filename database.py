import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

#環境変数を読み込む
load_dotenv()

# Renderから取得したデータベースURLを環境変数から取得
DATABASE_URL = os.getenv("DATABASE_URL")

#データベースエンジンを作成
engine = create_engine(DATABASE_URL)

#データベースとのセッションを管理するクラス
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# テーブルモデルのためのベースクラス
Base = declarative_base()
from sqlalchemy import Column, Integer, String
from .database import Base

# 'users'という名前のテーブルを定義するクラス
class User(Base):
    __tablename__ = "users"

    # テーブルの列(カラム)を定義
    id = Column(Integer, primary_key=True, index=True)# 自動で割り振られるID
    use_id = Column(String, unique=True, index=True)# LINEのユーザID
    city = Column(String) # ユーザが設定した都市名
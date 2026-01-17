# -*- coding: utf-8 -*-
"""
土壌雨量指数計算システム - WSGI エントリーポイント
Apache + mod_wsgi 用

使用方法:
  Apache設定で WSGIScriptAlias にこのファイルを指定
"""
import sys
import os

# アプリケーションのルートディレクトリを設定
application_root = os.path.dirname(os.path.abspath(__file__))

# Pythonパスに追加
sys.path.insert(0, application_root)
sys.path.insert(0, os.path.join(application_root, 'src'))

# 作業ディレクトリを変更（データファイル読み込みのため）
os.chdir(application_root)

# Flaskアプリケーションをインポート
from app import create_app

# WSGIアプリケーションオブジェクト（mod_wsgiが参照）
application = create_app(data_dir="data")

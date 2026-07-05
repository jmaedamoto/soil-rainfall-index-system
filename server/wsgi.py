# -*- coding: utf-8 -*-
"""
土壌雨量指数計算システム - WSGI エントリーポイント
Apache + mod_wsgi 用

使用方法:
  Apache設定で WSGIScriptAlias にこのファイルを指定
"""
import sys
import os
from pathlib import Path

# アプリケーションのルートディレクトリを設定
application_root = os.path.dirname(os.path.abspath(__file__))
application_path = Path(application_root).resolve()

default_cache_dir = (
    "/var/cache/myapp/staging/dosya"
    if "staging" in application_path.parts
    else "/var/cache/myapp/dosya"
)
os.environ.setdefault("CACHE_DIR", default_cache_dir)
os.environ.setdefault("SOIL_RAINFALL_API_PREFIX", "")

# Pythonパスに追加（インポート前に必要）
sys.path.insert(0, application_root)
sys.path.insert(0, os.path.join(application_root, 'src'))

# 作業ディレクトリを変更（データファイル読み込みのため）
os.chdir(application_root)

# Flaskアプリケーションをインポート（sys.path設定後）
from app import create_app

# WSGIアプリケーションオブジェクト（mod_wsgiが参照）
BASE = Path(__file__).resolve().parent
application = create_app(data_dir=str(BASE / "data"))

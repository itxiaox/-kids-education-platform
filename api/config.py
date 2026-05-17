import os
"""
配置模块
"""

# COS配置 - 从环境变量读取
COS_SECRET_ID = os.environ.get('COS_SECRET_ID', '')
COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY', '')
COS_BUCKET = os.environ.get('COS_BUCKET', 'itxiaox-1301580359')
COS_REGION = os.environ.get('COS_REGION', 'ap-shanghai')

# 视频分类
VIDEO_CATEGORIES = {
    'math': {'name': '数学思维', 'icon': '📐', 'path': 'private/02-learning/videos/math/'},
    'english': {'name': '英语启蒙', 'icon': '🔤', 'path': 'private/02-learning/videos/english/'},
    'pinyin': {'name': '拼音学习', 'icon': '🅰️', 'path': 'private/02-learning/videos/pinyin/'},
    'science': {'name': '科学探索', 'icon': '🔬', 'path': 'private/02-learning/videos/science/'},
}

# Flask配置
API_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
API_PORT = int(os.environ.get('FLASK_PORT', 5000))
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'web')
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')

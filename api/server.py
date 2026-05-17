# -*- coding: utf-8 -*-
"""
Flask API 服务器
提供视频列表、签名链接、搜索、播放记录等功能
"""

import os
import sys
import json
import time
import hashlib
import functools
from flask import Flask, jsonify, request, send_from_directory, Response
from qcloud_cos import CosConfig, CosS3Client

# 设置stdout编码以支持中文和emoji
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from config import (
    COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION,
    VIDEO_CATEGORIES, HISTORY_FILE, API_HOST, API_PORT, STATIC_FOLDER
)

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')

# 管理员配置
ADMIN_USERS = {
    'admin': hashlib.md5('admin123'.encode()).hexdigest()  # admin123 的MD5
}

# 存储已登录的token
ACTIVE_TOKENS = {}

def generate_token(username):
    """生成token"""
    token = hashlib.md5(f"{username}{time.time()}".encode()).hexdigest()
    ACTIVE_TOKENS[token] = {
        'username': username,
        'expires': time.time() + 3600 * 24  # 24小时过期
    }
    return token

def validate_token(token):
    """验证token"""
    if token not in ACTIVE_TOKENS:
        return None
    info = ACTIVE_TOKENS[token]
    if time.time() > info['expires']:
        del ACTIVE_TOKENS[token]
        return None
    return info['username']

def requires_auth(f):
    """装饰器：需要管理员认证"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization') or request.args.get('token')
        if not token:
            return jsonify({'code': 401, 'message': '未授权访问'}), 401
        
        username = validate_token(token)
        if not username:
            return jsonify({'code': 401, 'message': 'token无效或已过期'}), 401
        
        return f(*args, **kwargs)
    return decorated

# 初始化COS客户端（使用线程本地存储以支持多进程）
cos_client = None

def init_cos_client():
    """初始化COS客户端（确保在每个请求线程中都正确初始化）"""
    global cos_client
    if cos_client is not None:
        print(f"[DEBUG] cos_client already initialized")
        return
    print(f"[DEBUG] Initializing cos_client...")
    print(f"[DEBUG] COS_SECRET_ID: {'set' if COS_SECRET_ID else 'NOT SET'}")
    print(f"[DEBUG] COS_SECRET_KEY: {'set' if COS_SECRET_KEY else 'NOT SET'}")
    print(f"[DEBUG] COS_BUCKET: {COS_BUCKET}")
    print(f"[DEBUG] COS_REGION: {COS_REGION}")
    
    if not COS_SECRET_ID or not COS_SECRET_KEY:
        print("[DEBUG] cos_client not initialized - missing credentials")
        return
        
    if cos_client is None:
        try:
            cos_config = CosConfig(
                Region=COS_REGION,
                SecretId=COS_SECRET_ID,
                SecretKey=COS_SECRET_KEY
            )
            cos_client = CosS3Client(cos_config)
            print("[DEBUG] cos_client initialized successfully")
            # 测试连接
            try:
                cos_client.list_objects(Bucket=COS_BUCKET, Prefix='', MaxKeys=1)
                print("[DEBUG] COS connection test successful")
            except Exception as test_e:
                print(f"[DEBUG] COS connection test failed: {test_e}")
        except Exception as e:
            print(f"[ERROR] Failed to initialize cos_client: {type(e).__name__}: {e}")

# 在每个请求前确保cos_client已初始化
@app.before_request
def before_request():
    init_cos_client()


# Mock数据 - 用于演示模式
MOCK_VIDEOS = {
    'video/math/': [
        {'key': 'video/math/1.mp4', 'name': '认识数字1-10.mp4', 'size': 52428800, 'size_mb': 50.0, 'modified': '2024-01-15T10:30:00Z'},
        {'key': 'video/math/2.mp4', 'name': '加减法入门.mp4', 'size': 62914560, 'size_mb': 60.0, 'modified': '2024-01-16T14:20:00Z'},
        {'key': 'video/math/3.mp4', 'name': '形状认知.mp4', 'size': 41943040, 'size_mb': 40.0, 'modified': '2024-01-17T09:15:00Z'},
        {'key': 'video/math/4.mp4', 'name': '比较大小.mp4', 'size': 47185920, 'size_mb': 45.0, 'modified': '2024-01-18T11:00:00Z'},
    ],
    'video/english/': [
        {'key': 'video/english/1.mp4', 'name': '字母ABC.mp4', 'size': 52428800, 'size_mb': 50.0, 'modified': '2024-01-15T10:30:00Z'},
        {'key': 'video/english/2.mp4', 'name': '日常单词.mp4', 'size': 62914560, 'size_mb': 60.0, 'modified': '2024-01-16T14:20:00Z'},
        {'key': 'video/english/3.mp4', 'name': '简单对话.mp4', 'size': 41943040, 'size_mb': 40.0, 'modified': '2024-01-17T09:15:00Z'},
    ],
    'video/pinyin/': [
        {'key': 'video/pinyin/1.mp4', 'name': '声母学习.mp4', 'size': 52428800, 'size_mb': 50.0, 'modified': '2024-01-15T10:30:00Z'},
        {'key': 'video/pinyin/2.mp4', 'name': '韵母学习.mp4', 'size': 62914560, 'size_mb': 60.0, 'modified': '2024-01-16T14:20:00Z'},
        {'key': 'video/pinyin/3.mp4', 'name': '声调练习.mp4', 'size': 41943040, 'size_mb': 40.0, 'modified': '2024-01-17T09:15:00Z'},
        {'key': 'video/pinyin/4.mp4', 'name': '拼音组合.mp4', 'size': 47185920, 'size_mb': 45.0, 'modified': '2024-01-18T11:00:00Z'},
        {'key': 'video/pinyin/5.mp4', 'name': '整体认读音节.mp4', 'size': 57671680, 'size_mb': 55.0, 'modified': '2024-01-19T16:45:00Z'},
    ],
    'video/science/': [
        {'key': 'video/science/1.mp4', 'name': '认识动物.mp4', 'size': 52428800, 'size_mb': 50.0, 'modified': '2024-01-15T10:30:00Z'},
        {'key': 'video/science/2.mp4', 'name': '植物生长.mp4', 'size': 62914560, 'size_mb': 60.0, 'modified': '2024-01-16T14:20:00Z'},
        {'key': 'video/science/3.mp4', 'name': '天气变化.mp4', 'size': 41943040, 'size_mb': 40.0, 'modified': '2024-01-17T09:15:00Z'},
        {'key': 'video/science/4.mp4', 'name': '太阳系.mp4', 'size': 73400320, 'size_mb': 70.0, 'modified': '2024-01-18T11:00:00Z'},
    ]
}


def get_cos_files(prefix):
    """获取COS指定前缀下的所有文件"""
    if not cos_client:
        # 返回mock数据用于演示
        mock_data = MOCK_VIDEOS.get(prefix, [])
        print(f"[DEBUG] get_cos_files mock mode, prefix: '{prefix}', returning {len(mock_data)} files")
        return mock_data
    
    print(f"[DEBUG] get_cos_files real mode, bucket: '{COS_BUCKET}', prefix: '{prefix}'")
    files = []
    marker = ''
    while True:
        try:
            # 尝试使用新版SDK的list_objects_v2接口
            try:
                response = cos_client.list_objects_v2(
                    Bucket=COS_BUCKET,
                    Prefix=prefix,
                    ContinuationToken=marker if marker else None
                )
            except:
                # 兼容旧版SDK
                response = cos_client.list_objects(
                    Bucket=COS_BUCKET,
                    Prefix=prefix,
                    Marker=marker
                )
            
            print(f"[DEBUG] COS response keys: {[item['Key'] for item in response.get('Contents', [])]}")
            
            contents = response.get('Contents', [])
            if not contents:
                # 尝试不带末尾斜杠的前缀
                if prefix.endswith('/'):
                    alt_prefix = prefix[:-1]
                    print(f"[DEBUG] No contents with prefix '{prefix}', trying '{alt_prefix}'")
                    try:
                        response = cos_client.list_objects_v2(Bucket=COS_BUCKET, Prefix=alt_prefix)
                        contents = response.get('Contents', [])
                        print(f"[DEBUG] Alt prefix response keys: {[item['Key'] for item in contents]}")
                    except:
                        pass
                if not contents:
                    break
            
            for item in contents:
                key = item['Key']
                if not key.endswith('/'):  # 排除目录
                    files.append({
                        'key': key,
                        'name': os.path.basename(key),
                        'size': int(item['Size']),
                        'size_mb': round(int(item['Size']) / (1024 * 1024), 2),
                        'modified': item['LastModified']
                    })
            
            # 检查分页
            if response.get('IsTruncated') == 'true' or response.get('NextContinuationToken'):
                marker = response.get('NextMarker', '') or response.get('NextContinuationToken', '')
            else:
                break
        except Exception as e:
            print(f"[ERROR] 列出文件失败: {type(e).__name__}: {e}")
            break
    
    print(f"[DEBUG] Found {len(files)} files for prefix '{prefix}'")
    return files


def get_signed_url(key, expires=3600):
    """生成带签名的访问链接"""
    init_cos_client()
    if not cos_client:
        return None
    try:
        signed_url = cos_client.get_presigned_download_url(
            Bucket=COS_BUCKET,
            Key=key,
            Expired=expires
        )
        return signed_url
    except Exception as e:
        print(f"[ERROR] 生成签名链接失败: {e}")
        return None


def stream_video_from_cos(key):
    """从COS流式获取视频内容"""
    init_cos_client()
    if not cos_client:
        return None
    
    try:
        response = cos_client.get_object(
            Bucket=COS_BUCKET,
            Key=key,
        )
        return response['Body']
    except Exception as e:
        print(f"[ERROR] 从COS获取视频失败: {e}")
        return None


@app.route('/api/proxy/video/<path:path>', methods=['GET'])
def proxy_video(path):
    """代理转发视频流（永久访问方案）"""
    key = path
    
    if not key.startswith('private/') and not key.startswith('video/'):
        return jsonify({
            'code': 400,
            'message': '无效的视频路径'
        }), 400
    
    video_stream = stream_video_from_cos(key)
    if not video_stream:
        return jsonify({
            'code': 500,
            'message': '无法获取视频，请检查COS配置'
        }), 500
    
    def generate():
        try:
            while True:
                chunk = video_stream.read(8192)
                if not chunk:
                    break
                yield chunk
        except Exception as e:
            print(f"[ERROR] 视频流传输中断: {e}")
    
    filename = os.path.basename(key)

    return Response(
        generate(),
        mimetype='video/mp4',
        headers={
            'Content-Length': video_stream.total_size if hasattr(video_stream, 'total_size') else '',
            'Accept-Ranges': 'bytes',
            'Cache-Control': 'no-cache'
        }
    )


def load_history():
    """加载播放历史"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'history': []}
    return {'history': []}


def save_history(data):
    """保存播放历史"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存历史失败: {e}")
        return False


@app.route('/')
def index():
    """返回前端页面"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/videos', methods=['GET'])
def get_all_videos():
    """获取所有视频列表（过滤隐藏视频）"""
    category = request.args.get('category', '')
    
    # 获取隐藏视频列表
    hidden_list = get_hidden_list()
    
    # 演示模式：直接返回mock数据
    if not cos_client:
        all_files = []
        if category and category in VIDEO_CATEGORIES:
            prefix = VIDEO_CATEGORIES[category]['path']
            files = MOCK_VIDEOS.get(prefix, [])
            for f in files:
                f['category'] = category
                f['category_name'] = VIDEO_CATEGORIES[category]['name']
                f['category_icon'] = VIDEO_CATEGORIES[category]['icon']
            all_files = files
        else:
            for cat_key, cat_info in VIDEO_CATEGORIES.items():
                prefix = cat_info['path']
                files = MOCK_VIDEOS.get(prefix, [])
                for f in files:
                    f['category'] = cat_key
                    f['category_name'] = cat_info['name']
                    f['category_icon'] = cat_info['icon']
                all_files.extend(files)
        # 过滤隐藏视频
        all_files = [f for f in all_files if f['key'] not in hidden_list]
        all_files.sort(key=lambda x: (x['category'], x['name']))
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'categories': [
                    {
                        'key': k,
                        'name': v['name'],
                        'icon': v['icon'],
                        'path': v['path']
                    } for k, v in VIDEO_CATEGORIES.items()
                ],
                'videos': all_files,
                'total': len(all_files)
            }
        })
    
    all_files = []
    
    if category and category in VIDEO_CATEGORIES:
        prefix = VIDEO_CATEGORIES[category]['path']
        files = get_cos_files(prefix)
        for f in files:
            f['category'] = category
            f['category_name'] = VIDEO_CATEGORIES[category]['name']
            f['category_icon'] = VIDEO_CATEGORIES[category]['icon']
        all_files = files
    else:
        for cat_key, cat_info in VIDEO_CATEGORIES.items():
            files = get_cos_files(cat_info['path'])
            for f in files:
                f['category'] = cat_key
                f['category_name'] = cat_info['name']
                f['category_icon'] = cat_info['icon']
            all_files.extend(files)
    
    # 过滤隐藏视频
    all_files = [f for f in all_files if f['key'] not in hidden_list]
    
    # 按分类和名称排序
    all_files.sort(key=lambda x: (x['category'], x['name']))
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'categories': [
                {
                    'key': k,
                    'name': v['name'],
                    'icon': v['icon'],
                    'path': v['path']
                } for k, v in VIDEO_CATEGORIES.items()
            ],
            'videos': all_files,
            'total': len(all_files)
        }
    })


@app.route('/api/videos/<category>', methods=['GET'])
def get_category_videos(category):
    """获取指定分类的视频"""
    if category not in VIDEO_CATEGORIES:
        return jsonify({
            'code': 404,
            'message': f'分类 {category} 不存在'
        }), 404
    
    prefix = VIDEO_CATEGORIES[category]['path']
    files = get_cos_files(prefix)
    
    for f in files:
        f['category'] = category
        f['category_name'] = VIDEO_CATEGORIES[category]['name']
        f['category_icon'] = VIDEO_CATEGORIES[category]['icon']
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'category': category,
            'category_name': VIDEO_CATEGORIES[category]['name'],
            'category_icon': VIDEO_CATEGORIES[category]['icon'],
            'videos': files,
            'total': len(files)
        }
    })


@app.route('/api/video/<path:path>', methods=['GET'])
def get_video_url(path):
    """获取视频的签名访问链接"""
    expires = int(request.args.get('expires', 3600))

    # 构建COS路径
    key = f'video/{path}'

    signed_url = get_signed_url(key, expires)
    if signed_url:
        return jsonify({
            'code': 0,
            'message': 'success',
            'data': {
                'url': signed_url,
                'key': key,
                'expires': expires,
                'expires_in': f'{expires}秒'
            }
        })
    else:
        # 演示模式：返回提示
        return jsonify({
            'code': 200,
            'message': 'demo_mode',
            'data': {
                'url': None,
                'key': key,
                'demo': True,
                'message': '演示模式：需要配置COS凭证才能获取真实视频链接'
            }
        })


@app.route('/api/search', methods=['GET'])
def search_videos():
    """搜索视频"""
    keyword = request.args.get('keyword', '').strip().lower()
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '请提供搜索关键词'
        }), 400
    
    # 先获取所有视频
    all_videos = []
    for cat_key, cat_info in VIDEO_CATEGORIES.items():
        files = get_cos_files(cat_info['path'])
        for f in files:
            f['category'] = cat_key
            f['category_name'] = cat_info['name']
            f['category_icon'] = cat_info['icon']
            all_videos.append(f)
    
    # 搜索匹配
    results = [v for v in all_videos if keyword in v['name'].lower()]
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'keyword': keyword,
            'results': results,
            'total': len(results)
        }
    })


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取播放历史"""
    data = load_history()
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': data
    })


@app.route('/api/history', methods=['POST'])
def add_history():
    """添加播放记录"""
    req_data = request.get_json()
    
    if not req_data:
        return jsonify({
            'code': 400,
            'message': '请提供播放记录'
        }), 400
    
    video_name = req_data.get('video_name', '')
    video_path = req_data.get('video_path', '')
    category = req_data.get('category', '')
    duration = req_data.get('duration', 0)
    
    if not video_name:
        return jsonify({
            'code': 400,
            'message': '请提供视频名称'
        }), 400
    
    data = load_history()
    
    # 添加新记录
    record = {
        'id': int(time.time() * 1000),
        'video_name': video_name,
        'video_path': video_path,
        'category': category,
        'duration': duration,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 插入到最前面
    data['history'].insert(0, record)
    
    # 只保留最近100条
    if len(data['history']) > 100:
        data['history'] = data['history'][:100]
    
    save_history(data)
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': record
    })


@app.route('/api/history/<int:record_id>', methods=['DELETE'])
def delete_history(record_id):
    """删除单条播放记录"""
    data = load_history()
    
    original_len = len(data['history'])
    data['history'] = [h for h in data['history'] if h.get('id') != record_id]
    
    if len(data['history']) < original_len:
        save_history(data)
        return jsonify({
            'code': 0,
            'message': '删除成功'
        })
    else:
        return jsonify({
            'code': 404,
            'message': '记录不存在'
        }), 404


@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """清空播放历史"""
    save_history({'history': []})
    return jsonify({
        'code': 0,
        'message': '已清空播放历史'
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    all_videos = []
    for cat_key, cat_info in VIDEO_CATEGORIES.items():
        files = get_cos_files(cat_info['path'])
        all_videos.extend(files)
    
    total_size = sum(v['size'] for v in all_videos)
    
    # 读取播放历史
    history_data = load_history()
    watch_time = sum(h.get('duration', 0) for h in history_data['history'])
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'total_videos': len(all_videos),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
            'watched_count': len(history_data['history']),
            'total_watch_time': watch_time
        }
    })


# ==================== 管理员相关API ====================

@app.route('/history.html')
@app.route('/history')
def history_page():
    """返回播放历史页面"""
    history_html_path = os.path.join(app.static_folder, 'history.html')
    if os.path.exists(history_html_path):
        with open(history_html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return 'History page not found', 404

@app.route('/admin.html')
@app.route('/admin')
def admin_page():
    """返回管理页面"""
    admin_html_path = os.path.join(app.static_folder, 'admin.html')
    if os.path.exists(admin_html_path):
        with open(admin_html_path, 'r', encoding='utf-8') as f:
            return f.read()
    return 'Admin page not found', 404

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录"""
    req_data = request.get_json()
    username = req_data.get('username', '').strip()
    password = req_data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({
            'code': 400,
            'message': '请输入用户名和密码'
        }), 400
    
    # 验证密码
    expected_hash = ADMIN_USERS.get(username)
    if not expected_hash:
        return jsonify({
            'code': 401,
            'message': '用户名或密码错误'
        }), 401
    
    password_hash = hashlib.md5(password.encode()).hexdigest()
    if password_hash != expected_hash:
        return jsonify({
            'code': 401,
            'message': '用户名或密码错误'
        }), 401
    
    # 生成token
    token = generate_token(username)
    
    return jsonify({
        'code': 0,
        'message': '登录成功',
        'data': {
            'token': token,
            'username': username,
            'expires_in': 3600 * 24
        }
    })

@app.route('/api/admin/logout', methods=['POST'])
@requires_auth
def admin_logout():
    """管理员登出"""
    token = request.headers.get('Authorization') or request.args.get('token')
    if token in ACTIVE_TOKENS:
        del ACTIVE_TOKENS[token]
    
    return jsonify({
        'code': 0,
        'message': '登出成功'
    })

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    """检查登录状态"""
    token = request.headers.get('Authorization') or request.args.get('token')
    username = validate_token(token)
    
    if username:
        return jsonify({
            'code': 0,
            'message': '已登录',
            'data': {
                'username': username
            }
        })
    
    return jsonify({
        'code': 401,
        'message': '未登录'
    }), 401

@app.route('/api/admin/videos', methods=['GET'])
@requires_auth
def admin_get_videos():
    """管理员获取视频列表（包含隐藏状态）"""
    category = request.args.get('category', '')
    
    all_files = []
    for cat_key, cat_info in VIDEO_CATEGORIES.items():
        if category and category != cat_key:
            continue
        files = get_cos_files(cat_info['path'])
        for f in files:
            f['category'] = cat_key
            f['category_name'] = cat_info['name']
            f['category_icon'] = cat_info['icon']
            f['hidden'] = is_video_hidden(f['key'])
        all_files.extend(files)
    
    all_files.sort(key=lambda x: (x['category'], x['name']))
    
    return jsonify({
        'code': 0,
        'message': 'success',
        'data': {
            'videos': all_files,
            'total': len(all_files)
        }
    })

def is_video_hidden(key):
    """检查视频是否被隐藏"""
    hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
    if not os.path.exists(hidden_file):
        return False
    
    try:
        with open(hidden_file, 'r', encoding='utf-8') as f:
            hidden = json.load(f)
        return key in hidden.get('hidden', [])
    except:
        return False

def get_hidden_list():
    """获取所有隐藏视频的key列表"""
    hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
    if not os.path.exists(hidden_file):
        return []
    
    try:
        with open(hidden_file, 'r', encoding='utf-8') as f:
            hidden = json.load(f)
        return hidden.get('hidden', [])
    except:
        return []

def save_hidden_videos(hidden_list):
    """保存隐藏视频列表"""
    hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
    try:
        with open(hidden_file, 'w', encoding='utf-8') as f:
            json.dump({'hidden': hidden_list}, f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存隐藏列表失败: {e}")
        return False

@app.route('/api/admin/video/hide', methods=['POST'])
@requires_auth
def admin_hide_video():
    """隐藏视频"""
    req_data = request.get_json()
    key = req_data.get('key')
    
    if not key:
        return jsonify({
            'code': 400,
            'message': '请提供视频key'
        }), 400
    
    hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
    hidden_list = []
    
    if os.path.exists(hidden_file):
        try:
            with open(hidden_file, 'r', encoding='utf-8') as f:
                hidden = json.load(f)
                hidden_list = hidden.get('hidden', [])
        except:
            pass
    
    if key not in hidden_list:
        hidden_list.append(key)
    
    if save_hidden_videos(hidden_list):
        return jsonify({
            'code': 0,
            'message': '隐藏成功'
        })
    else:
        return jsonify({
            'code': 500,
            'message': '隐藏失败'
        }), 500

@app.route('/api/admin/video/show', methods=['POST'])
@requires_auth
def admin_show_video():
    """显示视频（取消隐藏）"""
    req_data = request.get_json()
    key = req_data.get('key')
    
    if not key:
        return jsonify({
            'code': 400,
            'message': '请提供视频key'
        }), 400
    
    hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
    hidden_list = []
    
    if os.path.exists(hidden_file):
        try:
            with open(hidden_file, 'r', encoding='utf-8') as f:
                hidden = json.load(f)
                hidden_list = hidden.get('hidden', [])
        except:
            pass
    
    if key in hidden_list:
        hidden_list.remove(key)
    
    if save_hidden_videos(hidden_list):
        return jsonify({
            'code': 0,
            'message': '已显示'
        })
    else:
        return jsonify({
            'code': 500,
            'message': '操作失败'
        }), 500

@app.route('/api/admin/video/delete', methods=['DELETE'])
@requires_auth
def admin_delete_video():
    """删除视频"""
    key = request.args.get('key')
    
    if not key:
        return jsonify({
            'code': 400,
            'message': '请提供视频key'
        }), 400
    
    # 演示模式：不实际删除
    if not cos_client:
        return jsonify({
            'code': 200,
            'message': 'demo_mode',
            'data': {
                'message': '演示模式：不会实际删除视频。在生产环境中，此操作将删除COS上的文件。'
            }
        })
    
    try:
        cos_client.delete_object(
            Bucket=COS_BUCKET,
            Key=key
        )
        
        # 从隐藏列表中移除
        hidden_file = os.path.join(os.path.dirname(__file__), 'hidden_videos.json')
        if os.path.exists(hidden_file):
            try:
                with open(hidden_file, 'r', encoding='utf-8') as f:
                    hidden = json.load(f)
                    hidden_list = hidden.get('hidden', [])
                if key in hidden_list:
                    hidden_list.remove(key)
                    save_hidden_videos(hidden_list)
            except:
                pass
        
        return jsonify({
            'code': 0,
            'message': '删除成功'
        })
    except Exception as e:
        print(f"删除视频失败: {e}")
        return jsonify({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }), 500


if __name__ == '__main__':
    print('[INFO] Starting Kids Education Platform API Server...')
    print('[INFO] Access URL: http://{}:{}'.format(API_HOST, API_PORT))
    print('[INFO] Frontend: http://{}:{}/'.format(API_HOST, API_PORT))
    app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False)
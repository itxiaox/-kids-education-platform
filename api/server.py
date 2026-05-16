"""
Flask API 服务器
提供视频列表、签名链接、搜索、播放记录等功能
"""

import os
import json
import time
from flask import Flask, jsonify, request, send_from_directory
from qcloud_cos import CosConfig, CosS3Client

from config import (
    COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION,
    VIDEO_CATEGORIES, HISTORY_FILE, API_HOST, API_PORT, STATIC_FOLDER
)

app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='/static')

# 初始化COS客户端
cos_config = CosConfig(
    Region=COS_REGION,
    SecretId=COS_SECRET_ID,
    SecretKey=COS_SECRET_KEY
)
cos_client = CosS3Client(cos_config)


def get_cos_files(prefix):
    """获取COS指定前缀下的所有文件"""
    files = []
    marker = ''
    while True:
        try:
            response = cos_client.list_objects(
                Bucket=COS_BUCKET,
                Prefix=prefix,
                Marker=marker
            )
            contents = response.get('Contents', [])
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
            if response.get('IsTruncated') == 'true':
                marker = response.get('NextMarker', '')
            else:
                break
        except Exception as e:
            print(f"列出文件失败: {e}")
            break
    return files


def get_signed_url(key, expires=3600):
    """生成带签名的访问链接"""
    try:
        # 使用get_presigned_download_url方法生成带签名的下载链接
        signed_url = cos_client.get_presigned_download_url(
            Bucket=COS_BUCKET,
            Key=key,
            Expired=expires
        )
        return signed_url
    except Exception as e:
        print(f"生成签名链接失败: {e}")
        return None


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
    """获取所有视频列表"""
    print("[DEBUG] get_all_videos called")
    category = request.args.get('category', '')
    print(f"[DEBUG] category param: '{category}'")
    
    all_files = []
    
    if category and category in VIDEO_CATEGORIES:
        print(f"[DEBUG] Single category mode: {category}")
        # 获取指定分类
        prefix = VIDEO_CATEGORIES[category]['path']
        print(f"[DEBUG] Calling get_cos_files with prefix: '{prefix}'")
        files = get_cos_files(prefix)
        print(f"[DEBUG] get_cos_files returned {len(files)} files")
        for f in files:
            f['category'] = category
            f['category_name'] = VIDEO_CATEGORIES[category]['name']
            f['category_icon'] = VIDEO_CATEGORIES[category]['icon']
        all_files = files
    else:
        print(f"[DEBUG] All categories mode, VIDEO_CATEGORIES has {len(VIDEO_CATEGORIES)} entries")
        # 获取所有分类
        for cat_key, cat_info in VIDEO_CATEGORIES.items():
            print(f"[DEBUG] Processing category: {cat_key}, path: {cat_info['path']}")
            files = get_cos_files(cat_info['path'])
            print(f"[DEBUG] get_cos_files for '{cat_key}' returned {len(files)} files")
            for f in files:
                f['category'] = cat_key
                f['category_name'] = cat_info['name']
                f['category_icon'] = cat_info['icon']
            all_files.extend(files)
    
    # 按分类和名称排序
    all_files.sort(key=lambda x: (x['category'], x['name']))
    
    print(f"[DEBUG] Total all_files: {len(all_files)}")
    
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
        return jsonify({
            'code': 500,
            'message': '获取视频链接失败'
        }), 500


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


if __name__ == '__main__':
    print(f'''
╔══════════════════════════════════════════════════════╗
║                                                      ║
║       🎬 幼升小教育动画学习平台 API 服务              ║
║                                                      ║
║       访问地址: http://{API_HOST}:{API_PORT}                   ║
║       前端页面: http://{API_HOST}:{API_PORT}/                   ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    ''')
    app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False)
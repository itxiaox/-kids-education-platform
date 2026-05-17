# -*- coding: utf-8 -*-
"""
SQLite数据库模块 - 管理视频资源
"""

import os
import sqlite3
import json
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), 'videos.db')

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库"""
    conn = get_db()
    cursor = conn.cursor()

    # 创建视频表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_key TEXT UNIQUE NOT NULL,
            video_name TEXT,
            video_path TEXT,
            thumbnail_key TEXT,
            size INTEGER,
            size_mb REAL,
            category TEXT,
            category_name TEXT,
            category_icon TEXT,
            upload_time TEXT,
            modified TEXT,
            hidden INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_video_key ON videos(video_key)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON videos(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hidden ON videos(hidden)')

    conn.commit()
    conn.close()

def sync_videos_from_cos(cos_files, category, category_name, category_icon):
    """从COS同步视频到数据库"""
    conn = get_db()
    cursor = conn.cursor()

    for file_info in cos_files:
        key = file_info['key']

        # 检查是否已存在
        cursor.execute('SELECT id FROM videos WHERE video_key = ?', (key,))
        exists = cursor.fetchone()

        # 构建缩略图路径：在thumbs子目录下同名.jpg
        video_name = key.split('/')[-1].rsplit('.', 1)[0]
        dir_path = key[:key.rfind('/')]
        thumbnail_key = f"{dir_path}/thumbs/{video_name}.jpg"

        if exists:
            # 更新
            cursor.execute('''
                UPDATE videos SET
                    video_name = ?,
                    video_path = ?,
                    thumbnail_key = ?,
                    size = ?,
                    size_mb = ?,
                    category = ?,
                    category_name = ?,
                    category_icon = ?,
                    upload_time = ?,
                    modified = ?
                WHERE video_key = ?
            ''', (
                file_info.get('name', ''),
                key,
                thumbnail_key,
                file_info.get('size', 0),
                file_info.get('size_mb', 0),
                category,
                category_name,
                category_icon,
                file_info.get('upload_time', ''),
                file_info.get('modified', ''),
                key
            ))
        else:
            # 新增
            cursor.execute('''
                INSERT INTO videos (
                    video_key, video_name, video_path, thumbnail_key,
                    size, size_mb, category, category_name, category_icon,
                    upload_time, modified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                key,
                file_info.get('name', ''),
                key,
                thumbnail_key,
                file_info.get('size', 0),
                file_info.get('size_mb', 0),
                category,
                category_name,
                category_icon,
                file_info.get('upload_time', ''),
                file_info.get('modified', '')
            ))

    conn.commit()
    conn.close()

def get_all_videos(include_hidden=False):
    """获取所有视频"""
    conn = get_db()
    cursor = conn.cursor()

    if include_hidden:
        cursor.execute('SELECT * FROM videos ORDER BY category, video_name')
    else:
        cursor.execute('SELECT * FROM videos WHERE hidden = 0 ORDER BY category, video_name')

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

def get_video_by_key(video_key):
    """根据key获取视频"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos WHERE video_key = ?', (video_key,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

def update_video_hidden(video_key, hidden):
    """更新视频隐藏状态"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE videos SET hidden = ? WHERE video_key = ?', (hidden, video_key))
    conn.commit()
    conn.close()

def get_hidden_list():
    """获取所有隐藏视频的key列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT video_key FROM videos WHERE hidden = 1')
    rows = cursor.fetchall()
    conn.close()

    return [row['video_key'] for row in rows]

def is_video_hidden(video_key):
    """检查视频是否隐藏"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT hidden FROM videos WHERE video_key = ?', (video_key,))
    row = cursor.fetchone()
    conn.close()

    return row['hidden'] == 1 if row else False

def delete_video(video_key):
    """删除视频"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM videos WHERE video_key = ?', (video_key,))
    conn.commit()
    conn.close()

def get_video_count():
    """获取视频数量"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM videos')
    row = cursor.fetchone()
    conn.close()

    return row['count'] if row else 0

def get_total_size():
    """获取总大小"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(size) as total FROM videos')
    row = cursor.fetchone()
    conn.close()

    return row['total'] if row and row['total'] else 0

def clear_all_videos():
    """清空所有视频"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM videos')
    conn.commit()
    conn.close()

# 初始化数据库
init_db()
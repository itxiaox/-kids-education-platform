# kids-education-platform

> 幼升小教育动画学习平台

## 项目简介

一个面向3-6岁儿童的在线教育动画学习平台，提供数学、英语、拼音、科学等分类动画视频的在线播放服务。

## 功能特性

- ✅ 视频分类展示（数学/英语/拼音/科学）
- 🔍 搜索视频功能
- 📺 在线播放视频
- 📝 播放记录追踪
- 🔄 自动同步COS存储桶视频列表

## 技术架构

```
前端 (HTML/CSS/JS)
    ↓ API请求
后端API (Flask)
    ↓ 签名生成
腾讯云COS (私有桶)
```

## 项目结构

```
kids-education-platform/
├── api/                 # 后端API
│   └── server.py       # Flask服务器
├── web/                # 前端页面
│   └── index.html      # 主页面
└── static/             # 静态资源
    ├── css/            # 样式文件
    ├── js/             # JavaScript
    └── images/          # 图片资源
```

## 快速启动

### 1. 安装依赖

```bash
pip install flask cos-python-sdk-v5
```

### 2. 配置COS凭证

在 `api/config.py` 中设置COS凭证：

```python
COS_SECRET_ID = 'your_secret_id'
COS_SECRET_KEY = 'your_secret_key'
COS_BUCKET = 'itxiaox-1301580359'
COS_REGION = 'ap-shanghai'
```

### 3. 启动服务

```bash
cd /opt/ai_company/project/kids-education-platform
python api/server.py
```

### 4. 访问

打开浏览器访问：`http://localhost:5000`

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/videos` | GET | 获取视频列表 |
| `/api/videos/<category>` | GET | 获取指定分类视频 |
| `/api/video/<path:path>` | GET | 获取视频播放链接（签名） |
| `/api/search` | GET | 搜索视频 |
| `/api/history` | POST | 记录播放历史 |
| `/api/history` | GET | 获取播放历史 |

## 配置说明

### 腾讯云COS

- Bucket: itxiaox-1301580359
- Region: ap-shanghai
- 视频路径: video/math/, video/english/, video/pinyin/, video/science/

### 播放记录存储

播放记录存储在 `api/history.json`

## License

MIT
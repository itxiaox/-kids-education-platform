/**
 * 幼升小教育动画学习平台 - 前端脚本
 */

// 全局状态
let allVideos = [];
let filteredVideos = [];
let currentCategory = 'all';
let currentPlaying = null;

// API基础URL
const API_BASE = '';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadVideos();
    loadHistory();
    loadStats();
    
    // 搜索框回车事件
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchVideos();
        }
    });
});

// 加载视频列表
async function loadVideos() {
    try {
        const response = await fetch(`${API_BASE}/api/videos`);
        const result = await response.json();
        
        if (result.code === 0) {
            allVideos = result.data.videos;
            filteredVideos = [...allVideos];
            renderVideos();
        } else {
            showError('加载视频失败');
        }
    } catch (error) {
        console.error('加载视频失败:', error);
        showError('网络错误，请刷新重试');
    }
}

// 加载统计数据
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/stats`);
        const result = await response.json();
        
        if (result.code === 0) {
            document.getElementById('totalVideos').textContent = result.data.total_videos;
            document.getElementById('totalSize').textContent = result.data.total_size_gb + ' GB';
            document.getElementById('watchedCount').textContent = result.data.watched_count;
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 切换分类
function switchCategory(category) {
    currentCategory = category;
    
    // 更新按钮状态
    document.querySelectorAll('.cat-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });
    
    // 筛选视频
    if (category === 'all') {
        filteredVideos = [...allVideos];
    } else {
        filteredVideos = allVideos.filter(v => v.category === category);
    }
    
    renderVideos();
}

// 渲染视频列表
function renderVideos() {
    const container = document.getElementById('videoList');
    
    if (filteredVideos.length === 0) {
        container.innerHTML = '<div class="loading">暂无视频</div>';
        return;
    }
    
    const categoryNames = {
        math: { name: '数学思维', icon: '📐' },
        english: { name: '英语启蒙', icon: '🔤' },
        pinyin: { name: '拼音学习', icon: '🅰️' },
        science: { name: '科学探索', icon: '🔬' }
    };
    
    let html = '<h2>📺 视频列表</h2><div class="video-grid">';
    
    filteredVideos.forEach(video => {
        const catInfo = categoryNames[video.category] || { name: video.category, icon: '📁' };
        html += `
            <div class="video-item" onclick="playVideo('${video.key}', '${video.name}', '${video.category}')">
                <div class="video-thumb">${catInfo.icon}</div>
                <h3>${video.name}</h3>
                <div class="meta">
                    <span class="category-tag">${catInfo.name}</span>
                    <span>${video.size_mb} MB</span>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 播放视频
async function playVideo(key, name, category) {
    try {
        // 去掉key中的video/前缀，因为API会自动添加
        const videoKey = key.replace(/^video\//, '');

        // 获取签名URL
        const response = await fetch(`${API_BASE}/api/video/${videoKey}`);
        const result = await response.json();

        if (result.code === 0) {
            currentPlaying = { key, name, category };

            // 显示播放器
            const playerSection = document.getElementById('playerSection');
            const videoPlayer = document.getElementById('videoPlayer');
            const currentVideoName = document.getElementById('currentVideoName');
            const playerInfo = document.getElementById('playerInfo');

            playerSection.style.display = 'block';
            currentVideoName.textContent = name;
            videoPlayer.src = result.data.url;

            playerInfo.innerHTML = `
                <span>📂 分类: ${getCategoryName(category)}</span> |
                <span>🔗 链接有效期: ${result.data.expires_in}</span>
            `;

            // 记录播放
            recordHistory(name, key, category);

            // 滚动到播放器
            playerSection.scrollIntoView({ behavior: 'smooth' });

            // 监听播放结束
            videoPlayer.onended = () => {
                updateHistoryDuration(key, Math.round(videoPlayer.duration));
            };
        } else if (result.code === 200 && result.message === 'demo_mode') {
            // 演示模式提示
            showError('演示模式：视频链接不可用。请配置COS凭证以获取真实视频。\n\n当前为演示数据，实际视频需要配置腾讯云COS。');
        } else {
            showError('获取视频链接失败');
        }
    } catch (error) {
        console.error('播放失败:', error);
        showError('播放失败，请重试');
    }
}

// 关闭播放器
function closePlayer() {
    const playerSection = document.getElementById('playerSection');
    const videoPlayer = document.getElementById('videoPlayer');
    
    videoPlayer.pause();
    videoPlayer.src = '';
    playerSection.style.display = 'none';
    currentPlaying = null;
}

// 搜索视频
async function searchVideos() {
    const keyword = document.getElementById('searchInput').value.trim();
    
    if (!keyword) {
        switchCategory(currentCategory);
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/api/search?keyword=${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.code === 0) {
            filteredVideos = result.data.results;
            
            if (filteredVideos.length === 0) {
                document.getElementById('videoList').innerHTML = 
                    '<div class="loading">未找到相关视频</div>';
            } else {
                renderVideos();
            }
        }
    } catch (error) {
        console.error('搜索失败:', error);
        showError('搜索失败，请重试');
    }
}

// 加载播放历史
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        const result = await response.json();
        
        if (result.code === 0) {
            renderHistory(result.data.history || []);
        }
    } catch (error) {
        console.error('加载历史失败:', error);
    }
}

// 渲染播放历史
function renderHistory(history) {
    const container = document.getElementById('historyList');
    
    if (history.length === 0) {
        container.innerHTML = '<div class="empty-tip">暂无播放记录</div>';
        return;
    }
    
    const categoryNames = {
        math: '📐',
        english: '🔤',
        pinyin: '🅰️',
        science: '🔬'
    };
    
    let html = '';
    history.slice(0, 20).forEach(item => {
        const icon = categoryNames[item.category] || '📁';
        html += `
            <div class="history-item" onclick="replayVideo('${item.video_path}', '${item.video_name}', '${item.category}')">
                <div class="history-icon">${icon}</div>
                <div class="history-info">
                    <div class="history-name">${item.video_name}</div>
                    <div class="history-time">${item.timestamp}</div>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 记录播放历史
async function recordHistory(name, path, category) {
    try {
        await fetch(`${API_BASE}/api/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_name: name,
                video_path: path,
                category: category,
                duration: 0
            })
        });
        loadHistory();
        loadStats();
    } catch (error) {
        console.error('记录历史失败:', error);
    }
}

// 更新观看时长
async function updateHistoryDuration(path, duration) {
    try {
        const response = await fetch(`${API_BASE}/api/history`);
        const result = await response.json();
        
        if (result.code === 0) {
            const history = result.data.history || [];
            const item = history.find(h => h.video_path === path);
            
            if (item) {
                item.duration = duration;
                await fetch(`${API_BASE}/api/history`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_name: item.video_name,
                        video_path: item.video_path,
                        category: item.category,
                        duration: duration
                    })
                });
            }
        }
    } catch (error) {
        console.error('更新时长失败:', error);
    }
}

// 重新播放
async function replayVideo(path, name, category) {
    await playVideo(path, name, category);
}

// 清空历史
async function clearHistory() {
    if (!confirm('确定要清空所有播放记录吗？')) return;
    
    try {
        await fetch(`${API_BASE}/api/history/clear`, { method: 'POST' });
        loadHistory();
    } catch (error) {
        console.error('清空历史失败:', error);
    }
}

// 获取分类名称
function getCategoryName(category) {
    const names = {
        math: '数学思维',
        english: '英语启蒙',
        pinyin: '拼音学习',
        science: '科学探索'
    };
    return names[category] || category;
}

// 显示错误
function showError(message) {
    alert(message);
}

// 格式化文件大小
function formatSize(bytes) {
    const mb = bytes / (1024 * 1024);
    if (mb >= 1024) {
        return (mb / 1024).toFixed(2) + ' GB';
    }
    return mb.toFixed(2) + ' MB';
}
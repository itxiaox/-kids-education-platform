/**
 * 后台管理系统 - 前端脚本
 */

let allVideos = [];
let filteredVideos = [];
const API_BASE = '';
const COS_BUCKET = '';
const COS_REGION = '';

// 生成视频缩略图URL（从COS获取）
function getThumbnailUrl(videoKey) {
    if (!COS_BUCKET || !COS_REGION) {
        return null;
    }
    // 缩略图与视频同名，但扩展名为.jpg
    const thumbnailKey = videoKey.replace(/\.[^.]+$/, '.jpg');
    return `/api/proxy/thumbnail/${encodeURIComponent(thumbnailKey)}`;
}

// 格式化时间显示
function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch {
        return dateStr;
    }
}

// 获取token
function getToken() {
    return localStorage.getItem('admin_token');
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    checkLogin();
});

// 检查登录状态
async function checkLogin() {
    const token = getToken();
    if (!token) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/admin/check`, {
            headers: { 'Authorization': token }
        });
        const result = await response.json();
        
        if (result.code !== 0) {
            localStorage.removeItem('admin_token');
            window.location.href = '/';
            return;
        }

        loadVideos();
    } catch (error) {
        console.error('检查登录失败:', error);
        localStorage.removeItem('admin_token');
        window.location.href = '/';
    }
}

// 加载视频列表
async function loadVideos() {
    const token = getToken();
    try {
        const response = await fetch(`${API_BASE}/api/admin/videos`, {
            headers: { 'Authorization': token }
        });
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
        showError('网络错误');
    }
}

// 渲染视频列表
function renderVideos() {
    const tbody = document.getElementById('videoTableBody');
    const emptyState = document.getElementById('emptyState');

    if (filteredVideos.length === 0) {
        tbody.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    const categoryIcons = {
        math: '📐',
        english: '🔤',
        pinyin: '🅰️',
        science: '🔬'
    };

    let html = '';
    filteredVideos.forEach((video, index) => {
        const icon = categoryIcons[video.category] || '📁';
        const status = video.hidden ? 'hidden' : 'visible';
        const statusText = video.hidden ? '❌ 已隐藏' : '✅ 显示中';
        const thumbnailUrl = getThumbnailUrl(video.key);
        const uploadTime = formatDate(video.modified);

        html += `
            <tr>
                <td>${index + 1}</td>
                <td>
                    ${thumbnailUrl ?
                        `<img src="${thumbnailUrl}" class="video-thumbnail" alt="${video.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='inline';">` : ''
                    }
                    <span class="thumb-placeholder" style="display:${thumbnailUrl ? 'none' : 'inline'};">${icon}</span>
                </td>
                <td title="${video.name}">${truncateText(video.name, 30)}</td>
                <td>${video.category_name}</td>
                <td>${video.size_mb} MB</td>
                <td>${uploadTime}</td>
                <td><span class="status status-${status}">${statusText}</span></td>
                <td>
                    ${video.hidden ?
                        `<button class="btn btn-show" onclick="toggleVideoShow('${video.key}')">显示</button>` :
                        `<button class="btn btn-hide" onclick="toggleVideoHide('${video.key}')">隐藏</button>`
                    }
                    <button class="btn btn-delete" onclick="handleDelete('${video.key}', '${video.name}')">删除</button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

// 过滤视频
function filterVideos() {
    const category = document.getElementById('categoryFilter').value;
    const status = document.getElementById('statusFilter').value;
    const keyword = document.getElementById('searchInput').value.toLowerCase().trim();

    filteredVideos = allVideos.filter(video => {
        if (category && video.category !== category) return false;
        if (status === 'visible' && video.hidden) return false;
        if (status === 'hidden' && !video.hidden) return false;
        if (keyword && !video.name.toLowerCase().includes(keyword)) return false;
        return true;
    });

    renderVideos();
}

// 隐藏视频
async function toggleVideoHide(key) {
    const token = getToken();
    try {
        const response = await fetch(`${API_BASE}/api/admin/video/hide`, {
            method: 'POST',
            headers: {
                'Authorization': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key })
        });
        const result = await response.json();

        if (result.code === 0) {
            loadVideos();
            showSuccess('隐藏成功');
        } else {
            showError(result.message || '隐藏失败');
        }
    } catch (error) {
        console.error('隐藏视频失败:', error);
        showError('网络错误');
    }
}

// 显示视频
async function toggleVideoShow(key) {
    const token = getToken();
    try {
        const response = await fetch(`${API_BASE}/api/admin/video/show`, {
            method: 'POST',
            headers: {
                'Authorization': token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key })
        });
        const result = await response.json();

        if (result.code === 0) {
            loadVideos();
            showSuccess('已显示');
        } else {
            showError(result.message || '操作失败');
        }
    } catch (error) {
        console.error('显示视频失败:', error);
        showError('网络错误');
    }
}

// 删除视频
async function handleDelete(key, name) {
    if (!confirm(`确定要删除视频 "${name}" 吗？此操作无法撤销！`)) {
        return;
    }

    const token = getToken();
    try {
        const response = await fetch(`${API_BASE}/api/admin/video/delete?key=${encodeURIComponent(key)}`, {
            method: 'DELETE',
            headers: { 'Authorization': token }
        });
        const result = await response.json();

        if (result.code === 0) {
            loadVideos();
            showSuccess('删除成功');
        } else if (result.code === 200 && result.message === 'demo_mode') {
            showInfo(result.data.message);
            loadVideos();
        } else {
            showError(result.message || '删除失败');
        }
    } catch (error) {
        console.error('删除视频失败:', error);
        showError('网络错误');
    }
}

// 退出登录
async function handleLogout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }

    const token = getToken();
    try {
        await fetch(`${API_BASE}/api/admin/logout`, {
            method: 'POST',
            headers: { 'Authorization': token }
        });
    } catch (error) {
        console.error('退出登录失败:', error);
    }

    localStorage.removeItem('admin_token');
    window.location.href = '/';
}

// 切换菜单
function switchMenu(menu) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.classList.add('active');

    if (menu === 'videos') {
        document.getElementById('pageTitle').textContent = '📺 视频管理';
        document.getElementById('videoContent').style.display = 'block';
    }
}

// 截断文本
function truncateText(text, maxLength) {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// 显示成功消息
function showSuccess(message) {
    alert('✅ ' + message);
}

// 显示错误消息
function showError(message) {
    alert('❌ ' + message);
}

// 显示提示消息
function showInfo(message) {
    alert('ℹ️ ' + message);
}
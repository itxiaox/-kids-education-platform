#!/bin/bash
# 幼升小教育动画学习平台 - 启动脚本

PROJECT_DIR="/opt/ai_company/project/kids-education-platform"

echo "🎬 启动幼升小教育动画学习平台..."
echo ""

# 进入项目目录
cd $PROJECT_DIR

# 杀掉旧进程
pkill -f "api/server.py" 2>/dev/null
sleep 1

# 启动服务
echo "🚀 启动API服务..."
/usr/bin/python3 api/server.py > /tmp/kids-education-server.log 2>&1 &
sleep 3

# 检查服务状态
if curl -s --max-time 5 http://localhost:5000/api/stats > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📺 访问地址："
    echo "   前端页面: http://localhost:5000/"
    echo "   API接口: http://localhost:5000/api/videos"
    echo ""
    echo "📁 项目目录: $PROJECT_DIR"
else
    echo "❌ 服务启动失败，请检查日志"
    tail -20 /tmp/kids-education-server.log
fi
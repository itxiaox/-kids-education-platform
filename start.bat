@echo off
echo 启动幼升小教育动画学习平台...
echo.

:: 设置COS环境变量（请替换为您的实际凭证）
set COS_SECRET_ID=your_secret_id_here
set COS_SECRET_KEY=your_secret_key_here
set COS_BUCKET=your_bucket_name_here
set COS_REGION=your_region_here

:: 启动服务
echo 正在启动API服务...
py api/server.py

pause
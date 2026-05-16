@echo off
echo 启动幼升小教育动画学习平台...
echo.

:: 设置COS环境变量
:: 请在运行前设置环境变量，或创建.env文件
:: 敏感信息请不要提交到GitHub！

:: 示例（实际使用时取消注释并替换为真实凭证）
:: set COS_SECRET_ID=your_secret_id_here
:: set COS_SECRET_KEY=your_secret_key_here
:: set COS_BUCKET=your_bucket_name
:: set COS_REGION=ap-shanghai

:: 启动服务
echo 正在启动API服务...
echo 提示：请确保已设置COS环境变量
echo.
py api/server.py

pause
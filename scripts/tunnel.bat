@echo off
chcp 65001 >nul
echo ================================
echo  启动 Cloudflare Tunnel (内网穿透)
echo ================================
echo.
echo 本脚本将 localhost:8000 暴露到公网
echo 请将输出的 URL 配置到飞书应用的事件订阅回调地址
echo.

cloudflared tunnel --url http://localhost:8000

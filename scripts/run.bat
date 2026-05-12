@echo off
chcp 65001 >nul
echo ================================
echo  启动 Trade-Wiki-AI 服务
echo ================================

call .venv\Scripts\activate.bat

echo [启动] FastAPI 服务 (http://localhost:8000) ...
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

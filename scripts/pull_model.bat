@echo off
chcp 65001 >nul
echo ================================
echo  拉取 Ollama 模型
echo ================================

:: 检查 Ollama
ollama --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Ollama，请先安装: https://ollama.com/download
    pause
    exit /b 1
)

echo [1/2] 拉取 Qwen2.5-7B-Instruct (Q4量化) ...
ollama pull qwen2.5:7b-instruct-q4_K_M

echo [2/2] 验证模型...
ollama list

echo.
echo 模型拉取完成！
pause

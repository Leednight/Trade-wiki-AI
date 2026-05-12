@echo off
chcp 65001 >nul
echo ================================
echo  Trade-Wiki-AI 环境安装
echo ================================

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 创建虚拟环境
if not exist ".venv" (
    echo [1/4] 创建虚拟环境...
    python -m venv .venv
) else (
    echo [1/4] 虚拟环境已存在，跳过
)

:: 激活虚拟环境
call .venv\Scripts\activate.bat

:: 升级 pip
echo [2/4] 升级 pip...
python -m pip install --upgrade pip

:: 安装依赖
echo [3/4] 安装项目依赖...
pip install -e ".[dev]" 2>nul || pip install -e .

:: 创建 .env 文件
if not exist ".env" (
    echo [4/4] 创建 .env 配置文件...
    copy .env.example .env
    echo [注意] 请编辑 .env 文件，填入 API Key 等配置
) else (
    echo [4/4] .env 已存在，跳过
)

:: 创建数据目录
if not exist "data\db" mkdir data\db
if not exist "data\chromadb" mkdir data\chromadb
if not exist "data\raw\books" mkdir data\raw\books
if not exist "data\raw\videos" mkdir data\raw\videos

echo.
echo ================================
echo  安装完成！
echo  下一步：
echo    1. 编辑 .env 填入配置
echo    2. 运行 scripts\pull_model.bat 拉取模型
echo    3. 运行 scripts\run.bat 启动服务
echo ================================
pause

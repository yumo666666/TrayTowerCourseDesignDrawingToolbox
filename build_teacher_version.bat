@echo off
setlocal

:: 设置虚拟环境名称
set VENV_NAME=venv

:: 检查虚拟环境是否存在
if not exist %VENV_NAME% (
    echo [INFO] 虚拟环境未找到，正在创建...
    python -m venv %VENV_NAME%
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败，请确保已安装 Python 并添加到 PATH。
        pause
        exit /b 1
    )
    echo [INFO] 虚拟环境创建成功。
) else (
    echo [INFO] 检测到现有虚拟环境。
)

:: 激活虚拟环境
call %VENV_NAME%\Scripts\activate
if errorlevel 1 (
    echo [ERROR] 无法激活虚拟环境。
    pause
    exit /b 1
)

:: 升级 pip
echo [INFO] 正在升级 pip...
python -m pip install --upgrade pip

:: 安装依赖
if exist requirement.txt (
    echo [INFO] 正在安装依赖...
    pip install -r requirement.txt
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败。
        pause
        exit /b 1
    )
) else (
    echo [WARNING] 未找到 requirement.txt，跳过依赖安装。
)

:: 执行打包
echo [INFO] 开始打包教师版...
pyinstaller --noconfirm --onefile --windowed ^
    --name "板式塔课设工具箱_教师版" ^
    --add-data "apps;apps" ^
    --add-data "features;features" ^
    main.py

if errorlevel 1 (
    echo [ERROR] 打包失败。
    pause
    exit /b 1
)

echo.
echo ==========================================
echo [SUCCESS] 打包完成！
echo 文件位置: dist\板式塔课设工具箱_教师版.exe
echo ==========================================
echo.

pause

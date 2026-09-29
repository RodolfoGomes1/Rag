@echo off
setlocal

title RAG - Consulta aos Manuais

cd /d "%~dp0"

echo.
echo ================================================
echo              RAG - INICIANDO
echo ================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado.
    echo.
    echo Execute primeiro:
    echo.
    echo     instalar_rag.bat
    echo.
    pause
    exit /b 1
)

if not exist "src\rag.py" (
    echo ERRO: src\rag.py nao encontrado.
    echo.
    pause
    exit /b 1
)

if not defined GEMINI_API_KEY (
    echo.
    echo ERRO: GEMINI_API_KEY nao configurada.
    echo.
    echo Execute novamente:
    echo.
    echo     instalar_rag.bat
    echo.
    pause
    exit /b 1
)

echo Iniciando RAG...
echo.

"venv\Scripts\python.exe" "src\rag.py"

echo.
echo ================================================
echo              RAG ENCERRADO
echo ================================================
echo.

pause
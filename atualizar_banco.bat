@echo off
setlocal

title RAG - Atualizar Banco

cd /d "%~dp0"

cls

echo.
echo ================================================================
echo                    RAG - ATUALIZAR BANCO
echo ================================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERRO: Ambiente Python nao encontrado.
    echo.
    echo Execute primeiro:
    echo.
    echo     instalar_rag.bat
    echo.
    pause
    exit /b 1
)

if not exist "src\criar_banco.py" (
    echo ERRO: src\criar_banco.py nao encontrado.
    echo.
    pause
    exit /b 1
)

if not exist "documentos" (
    echo ERRO: Pasta documentos nao encontrada.
    echo.
    pause
    exit /b 1
)

echo Iniciando atualizacao do banco...
echo.
echo Os PDFs da pasta documentos serao analisados.
echo.
echo Arquivos novos ou alterados serao indexados.
echo Arquivos que nao mudaram serao ignorados.
echo.

"venv\Scripts\python.exe" "src\criar_banco.py"

echo.
echo ================================================================
echo                  ATUALIZACAO FINALIZADA
echo ================================================================
echo.

pause
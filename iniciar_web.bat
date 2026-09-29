@echo off
setlocal

title RAG - Interface Web

:: Garante que o diretório de execução seja exatamente onde o .bat está (E:\RAG)
cd /d "%~dp0"

echo.
echo ================================================
echo         INICIANDO RAG - INTERFACE WEB
echo ================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo ERRO: Ambiente Python nao encontrado em venv\Scripts\python.exe
    echo Verifique se voce esta executando o .bat na pasta correta (E:\RAG).
    echo.
    pause
    exit /b 1
)

if not exist "app.py" (
    echo ERRO: Arquivo app.py nao encontrado nesta pasta!
    echo.
    pause
    exit /b 1
)

echo Iniciando o servidor Flask em segundo plano...
echo.

:: Inicia o Flask mantendo a janela do servidor separada para monitorar erros se houverem
start "Servidor RAG Flask" cmd /c "venv\Scripts\python.exe app.py & pause"

:: Aguarda 3 segundos para o servidor subir
timeout /t 3 /nobreak > nul

echo Abrindo o navegador em http://127.0.0.1:5000 ...
start http://127.0.0.1:5000

echo.
echo ================================================
echo         INTERFACE WEB INICIADA COM SUCESSO!
echo ================================================
echo Pode fechar esta janela. O servidor continuara rodando.
echo.

pause
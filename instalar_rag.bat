@echo off
setlocal EnableExtensions

title Instalador do RAG

cd /d "%~dp0"

echo.
echo ========================================================
echo                 INSTALADOR DO RAG
echo ========================================================
echo.
echo Pasta do projeto:
echo %CD%
echo.

REM ========================================================
REM CONFIGURACOES
REM ========================================================

set PYTHON_VERSION=3.14
set VENV=%CD%\venv
set REQUIREMENTS=%CD%\requirements.txt

REM ========================================================
REM 1 - VERIFICAR PYTHON
REM ========================================================

echo [1/7] Verificando Python...
echo.

python --version >nul 2>&1

if %errorlevel% equ 0 (
    echo Python encontrado:
    python --version
    goto PYTHON_OK
)

echo Python nao encontrado.
echo.

REM ========================================================
REM 2 - VERIFICAR WINGET
REM ========================================================

echo [2/7] Verificando WinGet...
echo.

winget --version >nul 2>&1

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo ERRO: WinGet nao esta disponivel.
    echo ========================================================
    echo.
    echo Este computador precisa do Windows Package Manager.
    echo.
    echo Alternativamente, instale o Python manualmente:
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

echo WinGet encontrado.
echo.

REM ========================================================
REM 3 - INSTALAR PYTHON INSTALL MANAGER
REM ========================================================

echo [3/7] Instalando Python Install Manager...
echo.

winget install 9NQ7512CXL7T -e --accept-package-agreements --accept-source-agreements --disable-interactivity

if %errorlevel% neq 0 (
    echo.
    echo O Python Install Manager pode ja estar instalado.
    echo Continuando...
    echo.
)

REM ========================================================
REM 4 - INSTALAR PYTHON 3.14
REM ========================================================

echo.
echo Instalando Python %PYTHON_VERSION%...
echo.

py install %PYTHON_VERSION%

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo ERRO: Nao foi possivel instalar o Python %PYTHON_VERSION%.
    echo ========================================================
    echo.
    echo Tente fechar este terminal e executar novamente.
    echo.
    pause
    exit /b 1
)

echo.
echo Python instalado.
echo.

:PYTHON_OK

REM ========================================================
REM 5 - CRIAR AMBIENTE VIRTUAL
REM ========================================================

echo [4/7] Criando ambiente virtual...
echo.

if exist "%VENV%\Scripts\python.exe" (
    echo Ambiente virtual ja existe.
) else (
    python -m venv "%VENV%"

    if %errorlevel% neq 0 (
        echo.
        echo ERRO ao criar ambiente virtual.
        echo.
        pause
        exit /b 1
    )

    echo Ambiente virtual criado.
)

REM ========================================================
REM 6 - INSTALAR BIBLIOTECAS
REM ========================================================

echo.
echo [5/7] Atualizando pip...
echo.

"%VENV%\Scripts\python.exe" -m pip install --upgrade pip

if %errorlevel% neq 0 (
    echo.
    echo ERRO ao atualizar pip.
    echo.
    pause
    exit /b 1
)

echo.
echo [6/7] Instalando bibliotecas do RAG...
echo.
echo Isso pode demorar alguns minutos.
echo.

if not exist "%REQUIREMENTS%" (
    echo.
    echo ERRO: requirements.txt nao encontrado.
    echo.
    pause
    exit /b 1
)

"%VENV%\Scripts\python.exe" -m pip install -r "%REQUIREMENTS%"

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo ERRO NA INSTALACAO DAS BIBLIOTECAS
    echo ========================================================
    echo.
    pause
    exit /b 1
)

REM ========================================================
REM 7 - CONFIGURAR GEMINI
REM ========================================================

echo.
echo [7/7] Verificando chave da Gemini...
echo.

if defined GEMINI_API_KEY (
    echo A variavel GEMINI_API_KEY ja esta configurada.
    echo.
    goto TESTAR_RAG
)

echo A chave da Gemini ainda nao esta configurada.
echo.
echo Ela sera salva como variavel de ambiente do usuario.
echo A chave NAO sera gravada dentro da pasta RAG.
echo.
echo Digite sua chave da Gemini.
echo.
set /p GEMINI_KEY="Chave Gemini: "

if "%GEMINI_KEY%"=="" (
    echo.
    echo Nenhuma chave foi informada.
    echo.
    echo O RAG foi instalado, mas a Gemini ainda nao foi configurada.
    echo.
    goto FINAL
)

echo.
echo Salvando chave da Gemini...

setx GEMINI_API_KEY "%GEMINI_KEY%" >nul

if %errorlevel% neq 0 (
    echo.
    echo ERRO ao salvar a chave.
    echo.
    pause
    exit /b 1
)

echo.
echo Chave configurada com sucesso.
echo.

REM ========================================================
REM TESTAR AMBIENTE
REM ========================================================

:TESTAR_RAG

echo.
echo Testando ambiente Python...
echo.

"%VENV%\Scripts\python.exe" -c "from google import genai; print('Google GenAI: OK')"

if %errorlevel% neq 0 (
    echo.
    echo ERRO: Google GenAI nao esta funcionando.
    echo.
    pause
    exit /b 1
)

"%VENV%\Scripts\python.exe" -c "import chromadb; print('ChromaDB: OK')"

if %errorlevel% neq 0 (
    echo.
    echo ERRO: ChromaDB nao esta funcionando.
    echo.
    pause
    exit /b 1
)

"%VENV%\Scripts\python.exe" -c "from sentence_transformers import SentenceTransformer; print('Sentence Transformers: OK')"

if %errorlevel% neq 0 (
    echo.
    echo ERRO: Sentence Transformers nao esta funcionando.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo                 INSTALACAO CONCLUIDA
echo ========================================================
echo.
echo Python:
"%VENV%\Scripts\python.exe" --version

echo.
echo Ambiente virtual:
echo %VENV%

echo.
echo Projeto:
echo %CD%

echo.
echo Para iniciar o RAG:
echo.
echo     iniciar_rag.bat
echo.

:FINAL

echo.
echo ========================================================
echo.
echo Pressione qualquer tecla para sair.
echo.

pause
exit /b 0
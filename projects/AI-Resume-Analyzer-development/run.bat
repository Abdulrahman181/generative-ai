@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

set "HOST=%HOST%"
if not defined HOST set "HOST=127.0.0.1"
set "PORT=%PORT%"
if not defined PORT set "PORT=8000"

where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required. Install Python 3 and try again.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the local virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 exit /b 1
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if not exist ".env" (
  for /f "delims=" %%A in ('powershell -NoProfile -Command "[Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Maximum 256 }))"') do set "SECRET_KEY=%%A"
  for /f "delims=" %%A in ('powershell -NoProfile -Command "'Admin-' + [guid]::NewGuid().ToString('N').Substring(0,18) + '!A1'"') do set "ADMIN_PASSWORD=%%A"
  >.env echo # Generated once by run.bat for local development. Do not commit this file.
  >>.env echo SECRET_KEY=%SECRET_KEY%
  >>.env echo ADMIN_USERNAME=admin
  >>.env echo ADMIN_EMAIL=admin@example.com
  >>.env echo ADMIN_PASSWORD=%ADMIN_PASSWORD%
  >>.env echo DATABASE_URL=sqlite:///./resume_analyzer.db
  >>.env echo ACCESS_TOKEN_EXPIRE_MINUTES=60
  >>.env echo CORS_ORIGINS=http://127.0.0.1:%PORT%,http://localhost:%PORT%
  >>.env echo GROQ_API_KEY=
  >>.env echo HF_TOKEN=
  echo.
  echo Created .env with a new local administrator account.
  echo Administrator username: admin
  echo Administrator email: admin@example.com
  echo Administrator password: %ADMIN_PASSWORD%
  echo Save these credentials; .env is ignored by Git.
  echo.
)

echo Starting AI Resume Analyzer at http://%HOST%:%PORT%/
python -m uvicorn main:app --host %HOST% --port %PORT%

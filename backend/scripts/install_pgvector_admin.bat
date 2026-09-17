@echo off
echo Installing pgvector into PostgreSQL 16...

copy /Y "%TEMP%\pgvector_ext\lib\vector.dll" "C:\Program Files\PostgreSQL\16\lib\" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] vector.dll copied
) else (
    echo [FAIL] Could not copy vector.dll
    pause
    exit /b 1
)

xcopy /Y "%TEMP%\pgvector_ext\share\extension\*" "C:\Program Files\PostgreSQL\16\share\extension\" >nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Extension SQL files copied
) else (
    echo [FAIL] Could not copy extension files
    pause
    exit /b 1
)

if exist "%TEMP%\pgvector_ext\include" (
    mkdir "C:\Program Files\PostgreSQL\16\include\server\extension\vector" 2>nul
    xcopy /Y /S "%TEMP%\pgvector_ext\include\server\extension\vector\*" "C:\Program Files\PostgreSQL\16\include\server\extension\vector\" >nul
    echo [OK] Header files copied
)

echo [DONE] pgvector installed. You may need to restart PostgreSQL.
net stop postgresql-x64-16 >nul 2>&1
net start postgresql-x64-16 >nul 2>&1
echo [OK] PostgreSQL restarted.
pause

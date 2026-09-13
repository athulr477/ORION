@echo off
echo ================================================
echo   Installing pgvector into PostgreSQL 16
echo ================================================

set PGROOT=C:\Program Files\PostgreSQL\16
set EXTRACT=%TEMP%\pgvector_ext

echo.
echo Copying vector.dll...
copy /Y "%EXTRACT%\lib\vector.dll" "%PGROOT%\lib\vector.dll"

echo Copying extension SQL files...
xcopy /Y /S "%EXTRACT%\share\extension\*" "%PGROOT%\share\extension\"

echo Creating include directory...
mkdir "%PGROOT%\include\server\extension\vector" 2>nul
xcopy /Y "%EXTRACT%\include\server\extension\vector\*" "%PGROOT%\include\server\extension\vector\"

echo.
echo Restarting PostgreSQL service...
net stop postgresql-x64-16
net start postgresql-x64-16

echo.
echo Enabling pgvector extension...
set PGPASSWORD=postgres
"%PGROOT%\bin\psql.exe" -U postgres -d orion_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
"%PGROOT%\bin\psql.exe" -U postgres -d orion_db -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo.
echo ================================================
echo   pgvector installation complete!
echo ================================================
pause

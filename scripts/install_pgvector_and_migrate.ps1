# Pgvector Installation Script - Run as Administrator
# Right-click this file -> Run with PowerShell (Run as administrator)

$ErrorActionPreference = "Stop"
$pgRoot = "C:\Program Files\PostgreSQL\16"
$extractPath = "$env:TEMP\pgvector_ext"

Write-Host "`n=== Installing pgvector for PostgreSQL 16 ===" -ForegroundColor Cyan

# 1. Copy DLL
Write-Host "Copying vector.dll..."
Copy-Item "$extractPath\lib\vector.dll" "$pgRoot\lib\" -Force
Write-Host "  [OK] vector.dll" -ForegroundColor Green

# 2. Copy extension SQL files
Write-Host "Copying extension SQL files..."
Copy-Item "$extractPath\share\extension\*" "$pgRoot\share\extension\" -Force
Write-Host "  [OK] Extension files" -ForegroundColor Green

# 3. Copy headers
Write-Host "Copying header files..."
New-Item -ItemType Directory -Path "$pgRoot\include\server\extension\vector" -Force | Out-Null
Copy-Item "$extractPath\include\server\extension\vector\*" "$pgRoot\include\server\extension\vector\" -Force
Write-Host "  [OK] Headers" -ForegroundColor Green

# 4. Restart PostgreSQL
Write-Host "Restarting PostgreSQL..."
Restart-Service postgresql-x64-16
Write-Host "  [OK] PostgreSQL restarted" -ForegroundColor Green

# 5. Create extension in orion_db
Write-Host "Creating vector extension in orion_db..."
$env:PGPASSWORD = 'orion_secret'
& "$pgRoot\bin\psql.exe" -U orion -d orion_db -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1
Write-Host "  [OK] Extension created" -ForegroundColor Green

# 6. Run Alembic migration
Write-Host "Running Alembic migrations..."
Set-Location "D:\PROJECTS\ORION"
& "D:\PROJECTS\ORION\.venv\Scripts\python.exe" -m alembic upgrade head
Write-Host "  [OK] Migrations complete" -ForegroundColor Green

Write-Host "`n=== DONE! pgvector installed and migrations applied ===" -ForegroundColor Green
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

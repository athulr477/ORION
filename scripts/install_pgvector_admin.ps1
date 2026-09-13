# Run this script as Administrator to install pgvector into PostgreSQL 16
# Right-click -> Run with PowerShell (as Administrator)

$pgRoot = "C:\Program Files\PostgreSQL\16"
$extractPath = "$env:TEMP\pgvector_ext"

Write-Host "Installing pgvector into PostgreSQL 16..." -ForegroundColor Cyan

# Copy DLL
Copy-Item "$extractPath\lib\vector.dll" "$pgRoot\lib\" -Force
Write-Host "  [OK] vector.dll copied to $pgRoot\lib\" -ForegroundColor Green

# Copy extension SQL files
Copy-Item "$extractPath\share\extension\*" "$pgRoot\share\extension\" -Force
Write-Host "  [OK] Extension SQL files copied to $pgRoot\share\extension\" -ForegroundColor Green

# Copy headers
New-Item -ItemType Directory -Path "$pgRoot\include\server\extension\vector" -Force | Out-Null
Copy-Item "$extractPath\include\server\extension\vector\*" "$pgRoot\include\server\extension\vector\" -Force
Write-Host "  [OK] Header files copied" -ForegroundColor Green

# Restart PostgreSQL
Write-Host "Restarting PostgreSQL service..." -ForegroundColor Cyan
Restart-Service postgresql-x64-16
Write-Host "  [OK] PostgreSQL restarted" -ForegroundColor Green

# Verify
$env:PGPASSWORD='postgres'
$result = & "$pgRoot\bin\psql.exe" -U postgres -d orion_db -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" 2>&1
Write-Host "`nVerification:" -ForegroundColor Cyan
Write-Host $result

Write-Host "`n[DONE] pgvector installed successfully!" -ForegroundColor Green
Write-Host "Press any key to close..."
$null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')

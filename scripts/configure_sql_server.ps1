# configure_sql_server.ps1
# Requires administrator privileges

$ErrorActionPreference = "Stop"

try {
    Write-Output "1. Enabling Mixed Mode Authentication..."
    Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL16.MSSQLSERVER\MSSQLServer" -Name LoginMode -Value 2
    Write-Output "SQL Server LoginMode set to Mixed Mode (2)."

    # Restart SQL Server to apply changes
    Write-Output "2. Restarting SQL Server service..."
    Restart-Service -Name MSSQLSERVER -Force
    Write-Output "SQL Server service restarted successfully."

    # Create SQL Login
    Write-Output "3. Generating secure password and creating SQL Login..."
    $password = "N8nSqlPwd_" + [guid]::NewGuid().ToString().Replace("-", "").Substring(0, 16) + "!"
    $connectionString = "Server=localhost;Database=master;Integrated Security=True;Encrypt=False"
    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()

    $sql = @"
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'n8n_sql_user')
BEGIN
    CREATE LOGIN [n8n_sql_user] WITH PASSWORD = '$password', DEFAULT_DATABASE = [master], CHECK_EXPIRATION = OFF, CHECK_POLICY = OFF;
END
ELSE
BEGIN
    ALTER LOGIN [n8n_sql_user] WITH PASSWORD = '$password';
END
ALTER SERVER ROLE [sysadmin] ADD MEMBER [n8n_sql_user];
"@

    $command = New-Object System.Data.SqlClient.SqlCommand($sql, $connection)
    $command.ExecuteNonQuery() | Out-Null
    $connection.Close()
    Write-Output "SQL Login 'n8n_sql_user' created/updated with sysadmin privileges."

    # Update .env file
    Write-Output "4. Updating .env file with new credentials..."
    $envPath = "d:\courses\Data Science\Data Engineering\n8n\.env"
    if (Test-Path $envPath) {
        $content = Get-Content $envPath -Raw
        $content = $content -replace 'MSSQL_USER=.*', "MSSQL_USER=n8n_sql_user"
        $content = $content -replace 'MSSQL_PASSWORD=.*', "MSSQL_PASSWORD=$password"
        $content = $content -replace 'MSSQL_DOMAIN=.*', "MSSQL_DOMAIN="
        Set-Content -Path $envPath -Value $content -NoNewline
        Write-Output ".env file updated successfully."
    } else {
        Write-Warning ".env file not found at $envPath."
    }

    Write-Output "`nSQL Server configuration complete! Press any key to close."
    Read-Host
} catch {
    Write-Error "An error occurred: $_"
    Read-Host
}

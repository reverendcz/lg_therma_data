# Jednoduché čtení Modbus TCP - parametrizovaná verze
# Použití: .\modbus_tcp.ps1 <IP> <registr> [interval] [timeout]

param(
    [Parameter(Mandatory=$true)]
    [string]$IP,
    
    [Parameter(Mandatory=$true)]  
    [int]$Registr,
    
    [Parameter(Mandatory=$false)]
    [int]$Interval = 5,
    
    [Parameter(Mandatory=$false)]
    [int]$Timeout = 1000
)

# === MAPOVÁNÍ REGISTRŮ ===
$registry = @{
    30001 = @{func=3; addr=0;   scale=1;      unit="";      name="Error Code"}
    30002 = @{func=3; addr=1;   scale=1;      unit="";      name="Operation Cycle"}  
    30003 = @{func=3; addr=2;   scale=0.1;    unit="°C";    name="Inlet Temperature"}
    30004 = @{func=3; addr=3;   scale=0.1;    unit="°C";    name="Outlet Temperature"}
    30005 = @{func=3; addr=4;   scale=0.1;    unit="°C";    name="DHW Circuit"}
    30006 = @{func=3; addr=5;   scale=0.1;    unit="°C";    name="DHW Tank"}
    30008 = @{func=3; addr=7;   scale=0.1;    unit="°C";    name="Room Temperature"}
    30009 = @{func=3; addr=8;   scale=0.055;  unit="l/min"; name="Water Flow"}
    30013 = @{func=3; addr=12;  scale=0.1;    unit="°C";    name="Outdoor Temperature"}
    40001 = @{func=4; addr=0;   scale=1;      unit="";      name="Operation Mode"}
    40003 = @{func=4; addr=2;   scale=0.1;    unit="°C";    name="Target Temp Circuit 1"}
    40009 = @{func=4; addr=8;   scale=0.1;    unit="°C";    name="DHW Target Temp"}
    40013 = @{func=4; addr=12;  scale=0.018;  unit="bar";   name="Water Pressure"}
    40018 = @{func=4; addr=17;  scale=0.00479; unit="kW";   name="Electrical Power"}
}

# Kontrola registru
if (-not $registry.ContainsKey($Registr)) {
    Write-Host "❌ Neznámý registr $Registr" -ForegroundColor Red
    Write-Host "Dostupné registry:" -ForegroundColor Yellow
    $registry.Keys | Sort-Object | ForEach-Object {
        Write-Host "  $_ - $($registry[$_].name)" -ForegroundColor Gray
    }
    exit 1
}

$reg_info = $registry[$Registr]

function Read-ModbusRegister {
    param($IP, $RegInfo, $Timeout)
    
    try {
        # TCP připojení
        $c = [Net.Sockets.TcpClient]::new()
        $c.ReceiveTimeout = $Timeout
        $c.Connect($IP, 502)
        $s = $c.GetStream()

        # Modbus TCP frame - Transaction ID, Protocol ID, Length, Unit ID, Function, Address, Count
        [byte[]]$query = 0,1,  0,0,  0,6,  1,  $RegInfo.func,  0,0,  0,1
        
        # Adresa jako 2 byty (big endian)
        $query[8] = [byte]([Math]::Floor($RegInfo.addr / 256))
        $query[9] = [byte]($RegInfo.addr % 256)

        # Odeslání
        $s.Write($query, 0, $query.Length)

        # Čtení odpovědi
        $response = New-Object byte[] 256
        $bytes_read = $s.Read($response, 0, $response.Length)

        # Uzavření
        $s.Close()
        $c.Close()

        # Dekódování (big endian)
        $raw = ($response[9] * 256) + $response[10]
        
        # Signed hodnoty
        if ($raw -gt 32767) { $raw = $raw - 65536 }
        
        return $raw
        
    } catch {
        throw $_.Exception.Message
    }
}

# Info o čtení
Write-Host "🔄 Čtu registr $Registr ($($reg_info.name)) z $IP" -ForegroundColor Green  
Write-Host "⏱️  Interval: $Interval s, Timeout: $Timeout ms" -ForegroundColor Cyan
Write-Host "⏹️  Zastavení: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Hlavní smyčka
while ($true) {
    try {
        $raw = Read-ModbusRegister -IP $IP -RegInfo $reg_info -Timeout $Timeout
        $value = [Math]::Round($raw * $reg_info.scale, 3)
        
        $timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "$timestamp  raw=$raw  value=$value$($reg_info.unit)" -ForegroundColor White
        
    } catch {
        $timestamp = Get-Date -Format "HH:mm:ss"  
        Write-Host "$timestamp  ❌ CHYBA: $_" -ForegroundColor Red
    }

    Start-Sleep -Seconds $Interval
}
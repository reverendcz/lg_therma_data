# LG Therma V Monitor v1.0.0
Verze testované jednotky LG model HU091MR.U44

🏠 **Komunitní monitoring tool pro LG Therma V tepelná čerpadla**

Kompletní Python nástroj pro sledování a analýzu tepelného čerpadla LG Therma V pomocí Modbus/TCP protokolu. Poskytuje přesné real-time monitoring všech klíčových parametrů s možnou kalibrací.

## 🚀 Rychlý start

### Instalace
```bash
git clone <repository>
cd lg_therma
pip install -r requirements.txt
```

### Základní použití
```bash
# Smooth monitoring (doporučeno)
python lgscan.py --smooth

# Dynamická tabulka s obnovováním
python lgscan.py --table --interval 10

# Jednoduchý přehled
python lgscan.py --simple
```

## 📋 Parametry spouštění

| Parametr | Popis | Příklad |
|----------|-------|---------|
| `--smooth` | Plynulé obnovování bez blikání (DOPORUČENO) | `python lgscan.py --smooth` |
| `--table` | Dynamická tabulka s obnovováním | `python lgscan.py --table` |
| `--simple` | Jednoduchý přehled základních hodnot | `python lgscan.py --simple` |
| `--interval X` | Interval obnovování v sekundách (default: 60s) | `python lgscan.py --smooth --interval 5` |
| `--once` | Jeden výpis a konec | `python lgscan.py --simple --once` |
| `--yaml FILE` | Vlastní konfigurační soubor | `python lgscan.py --yaml custom.yaml` |
| `--out FILE` | Uložení do CSV souboru | `python lgscan.py --out data.csv` |
| `--log FILE` | Logovací soubor | `python lgscan.py --log debug.log` |

### Příklady použití
```bash
# Kontinuální smooth monitoring s 5s intervalem
python lgscan.py --smooth --interval 5

# Dynamická tabulka s 10s intervalem a CSV záznamem
python lgscan.py --table --interval 10 --out monitoring.csv

# Jednorázový výpis do CSV
python lgscan.py --simple --once --out snapshot.csv

# Debug režim s logováním
python lgscan.py --smooth --interval 8 --log debug.log
```

## 🎯 Funkce

### ✅ Kompletní monitoring
- **28 registrů** pokrývajících všechny klíčové parametry
- **100% přesná kalibrace** všech hodnot
- **Real-time COP výpočet** (Coefficient of Performance)
- **Inteligentní diagnostika** chyb a stavů

### 📊 Sledované parametry

**Teploty (6 registrů)**
- Pokojová teplota
- Teploty vstup/výstup topení
- Teplota zásobníku TUV
- Venkovní teplota

**Hydraulika (5 registrů)**
- Průtok vody (kalibrace l/min)
- Tlak vody (kalibrace bar)
- Cílové teploty topení/TUV
- Elektrická spotřeba (přesná kalibrace kW)

**Stavy systému (17 registrů)**
- Silent mode nastavení/status
- Elektrické dohřevy (3 stupně)
- Stavy pumpy, kompresoru, odmrazování
- Diagnostické kódy a chyby
- Manuální ovládání

### 🖥️ Zobrazení

**Smooth Mode (--smooth)** - DOPORUČENO
- Plynulé obnovování pomocí ANSI escape sekvencí
- Žádné blikání obrazovky
- Perfektně zarovnaná tabulka
- Barevné rozlišení hodnot

**Table Mode (--table)**
- Dynamická tabulka s kompletním refresh
- Vhodné pro starší terminály
- Úplné vymazání a překreslování

**Simple Mode (--simple)**
- Jednoduchý textový výpis
- Pouze klíčové parametry
- Vhodné pro skripty a automatizaci

## ⚙️ Konfigurace

Konfigurace je v souboru `registers.yaml`:

```yaml
connection:
  host: 192.168.100.199  # IP adresa tepelného čerpadla
  port: 502              # Modbus TCP port
  unit: 1                # Modbus jednotka
  timeout: 3.0           # Timeout připojení
  delay_ms: 300          # Delay mezi registry

registers:
  - name: "Room Temperature"
    reg: 30008
    table: auto
    scale: 0.1
    unit: "°C"
  # ... dalších 27 registrů
```
## 📈 COP výpočet

Automatický výpočet Coefficient of Performance:
```
COP = Tepelný výkon / Elektrická spotřeba
```

**Podmínky platnosti COP:**
- Kompresor běží (status = 1)
- Odmrazování neběží (status = 0)
- Systém topí (režim = 2)

## 🛠️ Systémové požadavky

- Python 3.7+
- Windows/Linux/macOS
- Síťové připojení k LG Therma V
- Povolený Modbus/TCP na tepelném čerpadle

### Python závislosti
```
pymodbus==3.6.6
PyYAML==6.0.2
colorama==0.4.6
```

## 📁 Struktura projektu

```
lg_therma/
├── lgscan.py           # Hlavní monitoring program
├── modbus_tcp.py       # Python TCP nástroj (bez závislostí)
├── modbus_tcp.ps1      # PowerShell TCP nástroj (Windows)
├── registers.yaml      # Konfigurace registrů
├── requirements.txt    # Python závislosti
├── README.md          # Tento soubor
└── docs/              # Dokumentace
```

## 🔧 Jednoduché TCP nástroje

Pro rychlé čtení jednotlivých registrů bez složitých závislostí:

### PowerShell TCP nástroj (Windows)
```powershell
# Jednorázové čtení
.\modbus_tcp.ps1 192.168.100.199 30004 1 1000

# Kontinuální monitoring
.\modbus_tcp.ps1 192.168.100.199 30003 5 500
```

### Python TCP nástroj (multiplatform)
```bash
# Jednorázové čtení
python modbus_tcp.py 192.168.100.199 30004 0 1000

# Kontinuální monitoring
python modbus_tcp.py 192.168.100.199 40018 3 1000
```

**Výhody TCP nástrojů:**
- ✅ Žádné externí závislosti
- ✅ Přímý TCP socket přístup
- ✅ Rychlé připojení/odpojení
- ✅ Jednoduché použití

## 🎯 Výsledky

**Kompletně funkční monitoring tool s:**
- ✅ 100% přesnou kalibrací
- ✅ Dokonalým zarovnáním tabulky
- ✅ Smooth refresh bez blikání
- ✅ Kompletním 28-registrovým monitoringem
- ✅ Přesným COP výpočtem
- ✅ Profesionálním vzhledem
- ✅ Trojitým zobrazovacím režimem
- ✅ Flexibilní konfigurací

---

🏆 **PROJEKT KOMPLETNĚ DOKONČEN** 🏆
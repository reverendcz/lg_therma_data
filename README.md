# 🏆 LG Therma V Modbus Registry - Oficiální implementace

**Verze:** 2.1.2 | **Model:** HN091MR.U44 | **Status:** Testing

🏠 **Monitoring tool pro LG Therma V tepelná čerpadla**

Komplexní implementace Modbus registrů pro tepelné čerpadlo LG Therma V s pokročilým monitoringem, delta trackingem a COP výpočty. Všechny registry jsou ověřené proti skutečnosti a kalibrované pro přesné zobrazení hodnot.

📋 **Změny a história:** [CHANGELOG.md](CHANGELOG.md)


### Instalace
```bash
git clone https://github.com/reverendcz/lg_therma_data.git
cd lg_therma_data

# Doporučeno: použijte virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
```

### Použití
```bash
# Hlavní monitoring tool (doporučeno)
python lgscan.py --smooth --interval 10    # Plynulá tabulka s delta tracking
python lgscan.py --simple --interval 15    # Jednoduché zobrazení hlavních hodnot
python lgscan.py --once                     # Jednorázové čtení

# CSV export (monitoring s uložením dat)
python lgscan.py --smooth --interval 10 --out monitoring_$(Get-Date -Format 'yyyyMMdd_HHmmss').csv
python lgscan.py --simple --interval 30 --out simple_log.csv --log monitoring.log

# Jednoduchy rychlé čtení konkrétního registru
python modbus_tcp.py 192.168.1.100 30004          # Teplota výstupu
python modbus_tcp.py 192.168.1.100 30003 5        # Teplota vstupu každých 5s
.\modbus_tcp.ps1 192.168.1.100 40018 2 1000      # PowerShell verze
```

### ⚠️ Poznámky k použití
- **Smooth režim:** dynamicky se překresluje tabulka
- **Optimální interval:** 10-30 sekund pro stabilní výkon
- **Delta teploty:** Zobrazují se ve všech režimech (sloupec/footer/detail)

## 📋 Dostupné konfigurace

| Konfigurace | Registry | Úspěšnost | Doporučení |
|-------------|----------|-----------|------------|
| `registers.yaml` | 41 registrů | 41/41 (100%) | ✅ **DOPORUČENO** - Optimalizovaná konfigurace |

## 📁 Struktura projektu

```
lg_therma/
├── 📄 lgscan.py                        # ✅ Hlavní monitoring tool (pokročilý)
├── 📄 registers.yaml                   # ✅ Konfigurace registrů (41 optimalizovaných)
├── 📄 modbus_tcp.py                    # 🚀 Jednoduché čtení Python (bez závislostí)
├── 📄 modbus_tcp.ps1                   # 🚀 Jednoduché čtení PowerShell  
├── 📄 requirements.txt                 # Python dependencies
├── 📄 README.md                        # Tento soubor
├── 📁 docs/                            # Kompletní dokumentace
│   ├── 📄 HA_LG_ThermaV_Configuration.yaml # Home Assistant konfigurace
│   └── 📄 *.md                         # Technická dokumentace
└── 📁 .venv/                          # Python virtual environment
```

## 🛠️ Systémové požadavky

- **Python:** 3.7+
- **Síť:** Připojení k LG Therma V (IP: 192.168.100.199)
- **Modbus:** TCP port 502 aktivní

### Dependencies
```txt
# Pro lgscan.py (pokročilý monitoring)
pymodbus==3.6.6
PyYAML==6.0.2
colorama==0.4.6

# Pro modbus_tcp.py/.ps1 (jednoduché čtení)
# Žádné externí závislosti - používají čistý TCP socket
```


## 🚀 Jednoduché skripty (bez závislostí)

### `modbus_tcp.py` - Python bez externích knihoven
```bash
# Jednorázové čtení
python modbus_tcp.py 192.168.1.100 30004

# Kontinuální monitoring
python modbus_tcp.py 192.168.1.100 30003 5      # Každých 5 sekund
python modbus_tcp.py 192.168.1.100 40018 2 1000 # Každé 2s s timeoutem 1s
```

**Podporované registry:** 14 základních (teploty, průtok, tlak, výkon)

### `modbus_tcp.ps1` - PowerShell 
```powershell
# Jednorázové čtení  
.\modbus_tcp.ps1 192.168.1.100 30004

# Kontinuální monitoring
.\modbus_tcp.ps1 192.168.1.100 30003 5      # Každých 5 sekund
.\modbus_tcp.ps1 192.168.1.100 40018 2 1000 # Každé 2s s timeoutem 1s
.\powershell -ExecutionPolicy Bypass -File .\modbus_tcp.ps1 192.168.1.1 40018 0  # v případě že windows odmítnou spustit skript
```
## 📚 Dokumentace

Kompletní dokumentace v adresáři `docs/`:

---

**🔗 Repository:** [lg_therma_data](https://github.com/reverendcz/lg_therma_data)  
**📧 Contact:** Project maintainer  
**📅 Last Update:** 20. listopad 2025

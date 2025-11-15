# LG Therma V Modbus Monitor

Pokročilý nástroj pro monitoring tepelného čerpadla LG Therma V přes Modbus RTU/TCP protokol.

## 📋 Popis projektu

Program pro čtení registrů pomocí RS485 TO POE ETH (B) s jednotkou **LG Therma V tepelné čerpadlo 9 kW** typové označení **LG HN091MR.NK5**. 

⚠️ **Důležité upozornění:** Program byl vytvořen pouze pro čtení a ověření hodnot z registrů LG, může obsahovat nepřesné informace. Některé jednotky mají různé registry - co bylo vyčteno z konkrétní jednotky, to je implementováno.

## ✨ Klíčové funkce
- **28 registrů** - Kompletní monitoring teplot, hydrauliky, energie a stavů včetně tlaku vody
- **Dynamická tabulka** - Windows-kompatibilní real-time tabulkový display s barevným výstupem
- **Barevné delta monitoring** - Barevně odlišené změny s emoji indikátory  
- **CSV export** - Excel-kompatibilní formát s delta sledováním
- **Log soubory** - Detailní textové logy pro analýzu
- **Sledování spotřeby** - Přesné měření elektrické energie
- **Silent mode** - Monitoring nočního režimu
- **Záložní topení** - Sledování elektrických topných těles

## 🚀 Rychlý start

### Instalace
```bash
pip install -r requirements.txt
```

### Základní použití
```bash
# Jednorázové skenování
python lgscan.py --once

# Kontinuální monitoring (interval 30 sekund)  
python lgscan.py --interval 30

# Dynamická tabulka v real-time (doporučeno)
python lgscan.py --table --interval 10

# S CSV a log výstupem
python lgscan.py --interval 30 --out monitoring.csv --log monitoring.log
```

### Konfigurace
Hlavní konfigurační soubor: `registers.yaml` (28 registrů)

## 📊 Příklad výstupu
```
✓ [30008] Room Temperature 🏠: 20.0 °C (raw: 200, table: input)
✓ [30004] Heating Circuit OUTLET 🌡️: 27.8 °C 🔥(+0.3°C) (raw: 278, table: input)
✓ [40018] Electrical Power Consumption ⚡: 1.1 kW ⬇️(-0.1kW) (raw: 305, table: input)
✓ [10002] Water Pump Status 💧: 1.0 📈(0→1) (raw: 1, table: discrete)
```

## 🎯 Kalibrované registry (Nov 2025)

**Všechny hodnoty kalibrovány proti LG displeji - 100% přesnost:**
- **30009** - Průtok vody (škála: 0.055) 
- **40013** - Tlak vody (škála: 0.018)
- **40018** - Elektrická spotřeba (škála: 0.00479)
- **30006** - Teplota DHW nádrže (perfektní korelace)
- **30003** - Vstupní teplota (výborná korelace)
- **30004** - Výstupní teplota (dobrá korelace)

## 🔧 Klíčové registry
- **30008** - Teplota místnosti
- **30004** - Teplota výstup topného okruhu  
- **30009** - Průtok vody (l/min)
- **40013** - Tlak vody (bar)
- **40018** - Elektrická spotřeba (kW)
- **10002** - Stav oběhové pumpy
- **10004** - Stav kompresoru
- **00003/10008** - Silent mode ovládání/stav

## 🔧 Požadavky
- Python 3.7+
- pymodbus>=3.0.0
- PyYAML
- LG Therma V s povoleným Modbus RTU

## 📚 Dokumentace
- `docs/LG_ThermaV_Modbus.md` - Kompletní Modbus reference s Home Assistant integrací
- `docs/Calibration_Summary.md` - **Detailní kalibrace a validace (Nov 2025)**
- `docs/HA_Calibrated_Sensors.yaml` - Produkční Home Assistant konfigurace
- `LG_Therma_V_Registry_Documentation.md` - Původní dokumentace všech registrů
- `CHANGELOG.md` - Historie verzí a změn projektu

## 🎨 Barevné delta monitoring

Systém automaticky barevně odlišuje změny hodnot:
- **🔥🔴 Zvýšení teploty** - červená s fire emoji
- **❄️🔵 Snížení teploty** - modrá s snow emoji  
- **⬆️🟡 Zvýšení příkonu** - žlutá s up arrow
- **⬇️🟣 Snížení příkonu** - magenta s down arrow
- **📈🟢 Binární 0→1** - zelená s chart emoji
- **🔴 Binární 1→0** - červená
- **💪🔵 Zvýšení průtoku** - cyan s muscle emoji

## 📁 Struktura projektu

```
lg_therma/
├── README.md                              # Tento soubor
├── CHANGELOG.md                           # Historie verzí a změn
├── lgscan.py                              # Hlavní monitoring aplikace  
├── registers.yaml                         # Produkční konfigurace (28 registrů)
├── requirements.txt                       # Python závislosti
├── LG_Therma_V_Registry_Documentation.md  # Kompletní dokumentace registrů
├── .gitignore                            # Git ignore
└── docs/                                 # Dokumentace a reference
    └── LG_ThermaV_Modbus.md               # Modbus komunikační reference
    └── LG_Therma_V_Registry_Documentation.md # Detaily implementace a vývoje systému
```

## 💻 CSV formát

CSV výstup obsahuje sloupce:
- `ts` - Timestamp (ISO formát)
- `name` - Název registru
- `reg` - Číslo registru
- `table` - Typ tabulky (holding/input/discrete/coils)
- `raw` - Surová hodnota
- `scaled` - Škálovaná hodnota
- `unit` - Jednotka
- `delta` - Změna oproti předchozí hodnotě
- `previous_value` - Předchozí hodnota
- `ok` - Status čtení

## 🎛️ Příklady použití

### Základní monitoring
```bash
# Tabulkový režim (nejpřehlednější)
python lgscan.py --table --interval 10

# Standardní monitoring
python lgscan.py --interval 30 --out thermal_data.csv
```

### Debug režim
```bash
python lgscan.py --once --yaml registers.yaml
```

### S log souborem
```bash
python lgscan.py --table --interval 60 --out monitoring.csv --log thermal.log
```

## 🔄 Aktualizace

Systém je připraven pro produkční nasazení s kompletní sadou 28 registrů pokrývajících:
- Teplotní senzory (6x)
- Hydraulické parametry (3x) 
- Energetická data (1x)
- Stavy komponent (18x)

---

*Monitoring systém LG Therma V - připraven k produkčnímu nasazení*
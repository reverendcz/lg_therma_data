# LG Therma V Scanner

Nástroj pro čtení registrů LG Therma V přes Modbus/TCP, validaci (holding vs input), škálování a logování do CSV. Později rozšíříme o export do MariaDB/InfluxDB a dashboard v Grafaně.

## Popis projektu

Tento projekt implementuje CLI nástroj `lgscan.py` pro komunikaci s tepelnými čerpadly LG Therma V přes Modbus/TCP protokol. Nástroj podporuje:

- ✅ Čtení holding a input registrů
- ✅ Automatickou detekci typu registru ("auto" mód)
- ✅ Škálování hodnot podle konfigurace
- ✅ Export dat do CSV formátu
- ✅ Kontinuální monitorování s nastaveným intervalem
- ✅ Jednorázové skenování

## Instalace

### 1. Vytvořte virtuální prostředí

```bash
python -m venv .venv
```

### 2. Aktivujte virtuální prostředí

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 3. Nainstalujte závislosti

```bash
pip install -r requirements.txt
```

## Konfigurace

Upravte soubor `registers.yaml` podle vašeho nastavení:

```yaml
connection:
  host: 192.168.100.199  # IP adresa vašeho Modbus/TCP převodníku
  port: 502              # Port Modbus (obvykle 502)
  unit: 1                # Unit ID (obvykle 1)
  timeout: 2.0           # Timeout připojení
  delay_ms: 120          # Prodleva mezi dotazy (ms)

registers:
  - name: Water inlet temp
    reg: 30003
    table: holding       # holding | input | auto
    scale: 0.1
    unit: "°C"
```

### SSH tunel (pro vzdálený přístup)

Pokud běžíte mimo LAN, můžete použít SSH tunel:

```bash
ssh -N -L 1502:192.168.100.199:502 <user>@<server>
```

A v `registers.yaml` nastavte:
```yaml
connection:
  host: 127.0.0.1
  port: 1502
```

## Použití

### Jednorázové skenování
```bash
python lgscan.py --once --yaml registers.yaml --out scan.csv
```

### Kontinuální monitorování s intervalem
```bash
python lgscan.py --interval 10 --yaml registers.yaml --out scan.csv
```

### Parametry
- `--once` - Provede pouze jeden průchod
- `--interval N` - Interval mezi průchody v sekundách (default: 60)
- `--yaml FILE` - Cesta ke konfiguračnímu souboru (default: registers.yaml)
- `--out FILE` - Výstupní CSV soubor (default: scan.csv)

## Struktura projektu

```
lg_therma_data/
├── README.md          # Tento soubor
├── lgscan.py          # Hlavní skript
├── registers.yaml     # Konfigurace registrů
├── requirements.txt   # Python závislosti
├── .gitignore         # Git ignore
└── docs/              # Dokumentace a zdroje
```

## Výstupní CSV formát

CSV soubor obsahuje následující sloupce:

- `ts` - Timestamp (ISO format)
- `name` - Název registru
- `reg` - Číslo registru (30003, 40001, ...)
- `address0` - 0-based adresa pro Modbus
- `table` - Typ tabulky (holding/input)
- `raw` - Surová hodnota z Modbus
- `scaled` - Škálovaná hodnota
- `unit` - Jednotka
- `ok` - Úspěšnost čtení (True/False)
- `error` - Chybová zpráva (pokud ok=False)

## Požadavky

- Python 3.10+
- pymodbus==3.6.6
- PyYAML==6.0.2

## Přispívání

1. Fork projektu
2. Vytvořte feature branch (`git checkout -b feature/nova-funkce`)
3. Commitněte změny (`git commit -am 'Přidána nová funkce'`)
4. Push do branch (`git push origin feature/nova-funkce`)
5. Vytvořte Pull Request

## Licence

[Zde bude specifikována licence]

## Autoři

- [@reverendcz](https://github.com/reverendcz)

## Verze

- v0.1.0 - Inicializace projektu

---

*Tento README bude průběžně aktualizován podle vývoje projektu.*
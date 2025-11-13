# lg-thermav-scan

Nástroj pro periodické čtení registrů tepelného čerpadla LG Therma V pomocí Modbus/TCP, jejich validaci a ukládání do CSV souboru. V další fázi projektu budou přibývat exporty do MariaDB/InfluxDB a dashboardy v Grafaně.

## Požadavky

- Python 3.10+
- Balíčky uvedené v `requirements.txt`

## Instalace a rychlý start

1. Vytvořte a aktivujte virtuální prostředí:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
2. Upravte `registers.yaml` tak, aby odpovídal vaší síti (parametry `host`, `port`, `unit`).
3. První testovací běh:
   ```bash
   python lgscan.py --once --yaml registers.yaml --out scan.csv
   ```

### SSH tunel mimo lokální síť

Pokud se k bráně nemůžete připojit přímo, vytvořte SSH tunel z počítače v LAN:
```bash
ssh -N -L 1502:192.168.100.199:502 <user>@<core-srv>
```
V konfiguraci `registers.yaml` pak nastavte `host: 127.0.0.1` a `port: 1502`.

## Konfigurace registrů

Konfigurace je v `registers.yaml` a obsahuje sekci `connection` (host, port, unit, timeout, delay_ms) a seznam položek `registers`:

- `name`: popis registru
- `reg`: „lidské“ číslo registru (např. 30003)
- `table`: `holding`, `input` nebo `auto`
- `scale`: násobek použitý při převodu na finální jednotky
- `unit`: textová jednotka pro výstup

Adresy se při čtení převádějí na 0-based offset (např. `30003 → 2`). Režim `auto` preferuje holding registr a při chybě nebo nulové hodnotě zkusí vstupní registr.

## Použití

Jednorázový scan:
```bash
python lgscan.py --once --yaml registers.yaml --out scan.csv
```
Průběžný scan v intervalu 10 sekund:
```bash
python lgscan.py --interval 10 --yaml registers.yaml --out scan.csv
```

Volba `--yaml` ukazuje na konfigurační soubor (výchozí `registers.yaml`), `--out` určuje CSV výstup.

## CSV výstup

Každý řádek obsahuje sloupce:

- `ts`: čas UTC ve formátu ISO8601
- `name`: název registru
- `reg`: původní číslo registru
- `address0`: 0-based offset používaný pro Modbus
- `table`: tabulka, ze které byla hodnota načtena (`holding`, `input`)
- `raw`: číselná hodnota registru
- `scaled`: hodnota po vynásobení `scale`
- `unit`: textová jednotka
- `ok`: `True/False`, zda se podařilo přečíst hodnotu
- `error`: text chyby při selhání

Díky sloupci `scale` lze jednoduše doplnit nové registry z komunitních seznamů – přidejte položku do `registers.yaml`, nastavte správné číslo registru, režim tabulky a násobek.

## Struktura repozitáře

```
lg-thermav-scan/
├── .gitignore
├── lgscan.py
├── README.md
├── registers.yaml
└── requirements.txt
```

## Licence

Projekt je zveřejněn pod MIT licencí.

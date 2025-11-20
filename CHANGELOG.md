# Changelog

Všechny významné změny v LG Therma V monitoring systému budou dokumentovány v tomto souboru.

Formát je založen na [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
a tento projekt dodržuje [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.2] - 2025-11-20

### Přidáno
- **Nové diagnostické registry:** 5 nových registrů pro kompletnější monitoring
  - `30019` Suction Temperature - teplota sání kompresoru (diagnostika)
  - `30020` Inverter Discharge Temperature - teplota výstupu invertoru (servisní údaj)
  - `30021` Heat Exchanger Temperature - teplota výměníku tepla (diagnostika systému)
  - `30023` High Pressure (Refrigerant) - vysoký tlak chladiva (diagnostika kompresoru)
  - `30024` Low Pressure (Refrigerant) - nízký tlak chladiva (diagnostika okruhu)
  - `30025` Inverter Frequency - frekvence invertoru kompresoru (0=vypnuto, 30-50 Hz normál, až 75 Hz max)
- **Nástroje pro objevování registrů:** Vytvořeny pokročilé scanner nástroje pro mapování Modbus registrů
  - `scanner/input_register_scanner.py` - automatické skenování Input registrů (3xxxx)
  - `scanner/holding_scanner.py` - rychlé skenování Holding registrů (4xxxx)  
  - `scanner/register_monitor.py` - real-time monitoring objevených registrů s detekcí změn
  - `scanner/inverter_monitor.py` - specializovaný monitor frekvence invertoru
- **Kompletní registry mapping:** Definitivní zmapování LG Therma V systému - 39 přístupných registrů identifikováno

### Opraveno
- **Kritická oprava cílových teplot:** Opraveno čtení uživatelem nastavených teplot z ovladače
  - `40003` Target Temperature Heating/Cooling: `table: input` → `table: holding`
  - `40009` DHW Target Temperature: `table: input` → `table: holding`
  - Nyní správně zobrazuje cílové teploty nastavené uživatelem na ovladači
  - 40003 nyní čte 25°C místo 0°C, 40009 nyní čte 45°C místo 23.6°C

### Testováno a ověřeno
- **Registr 30025:** Ověřena funkčnost frekvence invertoru pomocí real-time testů
  - Test 1: Normální provoz (38 Hz)
  - Test 2: Zvýšení teploty (38 → 41 → 48 Hz)
  - Test 3: Vypnutí systému (48 → 0 Hz)
- **Scanner nástroje:** Kompletní prohledání registrových rozsahů
  - 30001-30025: 25 funkčních Input registrů
  - 30026-30120: Prázdné rozsahy potvrzeny
  - 40001-40023: 23 Holding registrů (většina prázdných)
  - 40063-40064: 2 diagnostické registry
  - Definitivní zjištění: Pouze registr 30018 poskytuje energetická data

### Technické detaily
- **Holding vs Input registr problém:** Cílové teploty jsou WRITE hodnoty → musí být `holding`
- **Registry tlaků chladiva:** Poskytují diagnostiku zdraví kompresoru a chladicího okruhu
- **Teploty kompresoru:** Umožňují monitoring přehřátí a výkonnosti invertoru
- **Inverter frekvence monitoring:** Klíčová metrika pro sledování zatížení kompresoru v reálném čase
- **Registry scanning optimalizace:** Timeout optimalizace z 2.0s na 0.5s pro efektivní objevování
- **Celkem registrů:** Navýšeno z 41 na 46 aktivních registrů pro maximální diagnostiku
- **Kompletní mapping:** LG Therma V má pouze 39 přístupných registrů - žádná skrytá energetická data nejsou dostupná

## [2.1.1] - 2025-11-20

### Opraveno
- **Kritická oprava čtení 4xxxx registrů:** Opraveno nesprávné čtení Input registrů (4xxxx) jako Holding registrů
  - Registry 40003, 40004, 40005, 40009, 40013 nyní správně používají `table: input` místo `table: holding`
  - Registr 40013 (Water Pressure) nyní čte skutečné hodnoty (0.45-0.58 bar) místo nulových hodnot
  - Oprava podle Modbus konvence: 4xxxx = Input Registers (function 4), 3xxxx = Holding Registers (function 3)
- **Diagnostika a ladění:** Identifikován rozdíl mezi `lgscan.py` (pymodbus) a `modbus_tcp.py` (TCP socket)

### Technické detaily
- `lgscan.py` má implementovanou podporu pro různé typy registrů (`holding`, `input`, `discrete`, `coils`, `auto`)
- Problem byl v nesprávné konfiguraci v `registers.yaml`, ne v samotném kódu
- Všechny 4xxxx registry nyní používají správný function code 4 (Read Input Registers)

## [2.1.0] - 2025-11-20

### Přidáno
- **Standalone skripty:** `modbus_tcp.py` a `modbus_tcp.ps1` pro rychlé čtení registrů bez závislostí
- **CSV export:** Kompletní dokumentace exportu dat do CSV formátu v README.md
- **Home Assistant integrace:** Kompletní konfigurace v `docs/HA_LG_ThermaV_Configuration.yaml`

### Změněno
- **Odstranění table režimu:** Odebrán `--table` režim, ponechány pouze `--smooth` a `--simple`
- **Čistší delta sloupec:** Odstraněny emotikony z delta změn pro lepší čitelnost
- **Optimalizace:** 41 sledovaných registrů optimalizovaných pro reálné použití

### Opraveno
- **Kalibrace registrů:** Doladěny scaling faktory pro lepší přesnost měření
- **Padding alignace:** Opraveno zarovnání delta sloupce v tabulkovém výstupu

## [2.0.0] - 2025-11-19

### Přidáno
- **Nový monitoring systém:** Kompletní přepsání pro LG Therma V heat pump
- **Multi-režimy:** `--simple`, `--smooth`, `--table` režimy zobrazení
- **Delta tracking:** Sledování změn hodnot s vizuálním označením
- **YAML konfigurace:** Centralizovaná konfigurace všech registrů v `registers.yaml`
- **Robust error handling:** Pokročilé zpracování chyb s retry logikou

### Technické specifikace
- **Modbus TCP:** Komunikace přes IP 192.168.100.199:502
- **41 registrů:** Kompletní monitoring všech důležitých parametrů
- **Python 3.8+:** Kompatibilita s moderními verzemi Python
- **Pymodbus 3.x:** Využití nejnovější verze Modbus knihovny

---

## Verze a tagy

- `v2.1.1` - Kritická oprava Input registrů (aktuální)
- `v2.1.0` - Finalizovaná verze se standalone skripty
- `v2.0.0` - Základní LG Therma V monitoring systém

## Migrace a kompatibilita

### Z verze 2.1.0 na 2.1.1
- Pouze oprava konfigurace - žádné změny v API
- Automaticky opraveno čtení tlaku vody a teplotních senzorů

### Z verze 1.x na 2.0.0
- Kompletní přepis - není zpětně kompatibilní
- Nový systém konfigurace přes YAML
- Jiné parametry příkazové řádky
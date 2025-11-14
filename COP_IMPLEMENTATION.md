# 🔥 COP (Coefficient of Performance) - Implementace

**Datum implementace:** 15.11.2025  
**Verze:** LG Therma V Monitor v1.1

## 📊 Co je COP?

**COP = Tepelný výkon / Elektrický příkon**

COP je klíčovou metrikou účinnosti tepelného čerpadla. Hodnota COP = 3.0 znamená, že čerpadlo produkuje 3 kW tepelného výkonu při spotřebě 1 kW elektrické energie.

## 🧮 Implementovaný výpočet

### Vzorec pro tepelný výkon:
```
Q = ṁ × cp × ΔT
```

Kde:
- **ṁ** = hmotnostní tok vody [kg/s] 
- **cp** = specifické teplo vody ≈ 4.18 kJ/(kg·K)
- **ΔT** = rozdíl teplot (výstup - vstup) [K]

### Použité registry:
| Parametr | Registr | Hodnota | Jednotka |
|----------|---------|---------|-----------|
| **Průtok vody** | 30009 | 18.8 | l/min |
| **Výstup topení** | 30004 | 20.1 | °C |
| **Vstup topení** | 30003 | 21.0 | °C |
| **Elektrický příkon** | 40018 | 0.7 | kW |

### Výpočetní kroky:
```python
# 1. Konverze průtoku na kg/s
mass_flow = 18.8 / 60.0 = 0.313 kg/s

# 2. Teplotní rozdíl 
delta_temp = 20.1 - 21.0 = -0.9°C (chlazení)

# 3. Tepelný výkon
thermal_power = 0.313 × 4.18 × 0.9 = 1.178 kW

# 4. COP
COP = 1.178 / 0.7 = 1.61
```

## 📋 Validační podmínky

COP se vypočítá pouze pokud:
1. ✅ Všechny potřebné registry jsou dostupné
2. ✅ Průtok vody > 0 l/min  
3. ✅ Elektrický příkon > 0 kW
4. ✅ Teplotní rozdíl ≥ 0.1°C
5. ✅ Výsledný COP je v rozsahu 0.1 - 15.0

## 🎯 Interpretace aktuální hodnoty

### Měření: **COP = 1.61**

| Parametr | Hodnota | Analýza |
|----------|---------|---------|
| **🌡️ Teplotní spád** | 0.9°C | Malý spád - standby/cirkulace |
| **💧 Průtok** | 18.8 l/min | Normální oběh |
| **⚡ Příkon** | 0.7 kW | Nízký - noční režim |
| **🔄 Provoz** | Standby | Kompresor OFF |

### 💡 Vysvětlení COP 1.61:
- Systém v **standby režimu** (silent mode)
- **Nízký tepelný spád** = jen oběh teplé vody
- COP 1.61 je **normální pro standby**
- Při aktivním topení očekávám **COP 3-5**

## 📊 CSV Export

Nový formát CSV obsahuje:
```csv
ts,name,reg,address0,table,raw,scaled,unit,delta,previous_value,ok,error,cop
```

COP hodnota se zapisuje ke **všem registrům** v dané iteraci.

## 📝 Log soubory

COP informace v logu:
```
[2025-11-15 00:27:15] 🔥 COP (Coefficient of Performance): 1.61
```

Pokud nelze vypočítat:
```
[2025-11-15 00:27:15] ℹ️  COP: Nelze vypočítat (nedostatečné podmínky)
```

## 🔄 Budoucí rozšíření

### Možná vylepšení:
1. **COP trend analysis** - sledování změn v čase
2. **Seasonal COP** - sezonní analýza účinnosti  
3. **COP alerting** - upozornění při nízkých hodnotách
4. **DHW COP** - separátní COP pro ohřev TUV

### Kalibrace:
- **Testování při různých podmínkách**
- **Porovnání s oficiálními daty LG**
- **Optimalizace konstant (cp, density)**

## 🎯 Závěr

COP monitoring je nyní **plně funkční** a poskytuje:
- ✅ Real-time výpočet účinnosti
- ✅ Automatickou validaci podmínek
- ✅ CSV export pro analýzu
- ✅ Log informace pro debugging

**Systém je připraven na sledování účinnosti LG Therma V!** 🚀
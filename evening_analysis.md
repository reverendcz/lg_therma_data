# 🌆 VEČERNÍ ANALÝZA před nočním režimem
**Čas:** 14.11.2025, 19:21:45  
**Status:** Pre-silent mode analysis (noční režim od 20:00)

## 📊 POROVNÁNÍ: RÁNO vs. VEČER

| Parametr | Ráno (00:05) | Večer (19:21) | Delta | Status |
|----------|--------------|---------------|--------|---------|
| 🏠 **Room Temperature** | 19.5°C | **18.5°C** | ❄️**-1.0°C** | Pokles během dne |
| 🌡️ **Heating OUTLET** | 24.2°C | **19.4°C** | ❄️**-4.8°C** | Výrazný pokles |
| 🌡️ **Heating INLET** | 22.0°C | **21.0°C** | ❄️**-1.0°C** | Mírný pokles |
| 🚿 **DHW Tank** | 43.9°C | **40.5°C** | ❄️**-3.4°C** | Využitá během dne |
| 🌤️ **Outdoor Temp** | 3.9°C | **5.0°C** | 🔥**+1.1°C** | Oteplení |
| ⚡ **Power Consumption** | 0.8 kW | **0.7 kW** | ⬇️**-0.1kW** | Mírný pokles |

## 🔍 KLÍČOVÉ ZMĚNY

### ✨ Pozitivní změny
1. **🌤️ Venkovní teplota +1.1°C** (3.9°C → 5.0°C)
   - Lepší podmínky pro tepelné čerpadlo
   - Vyšší efektivita očekávána

2. **💧 Water Flow Status: 0 → 1** 
   - Flow detection aktivní
   - Systém detekuje průtok

3. **🔄 Operation Cycle: 0 → 2**
   - Změna provozního stavu
   - Systém v jiné fázi cyklu

### ⚠️ Významné změny
1. **🏠 Room temp pokles o 1°C** (19.5°C → 18.5°C)
   - Normální během dne
   - Potřeba večerního vytápění

2. **🌡️ Heating outlet -4.8°C** (24.2°C → 19.4°C)
   - Systém momentálně netopí
   - Outlet ≈ room temperature

3. **🚿 DHW pokles -3.4°C** (43.9°C → 40.5°C)
   - Využití teplé vody během dne
   - Stále v použitelném rozsahu

## 🔧 SYSTÉMOVÉ STAVY

### 🌙 Silent Mode Status
- **Setting:** OFF (0) - Normal mode
- **Status:** OFF (0) - Ještě není 20:00

### 💧 Hydraulika
- **Oběhové čerpadlo:** ON (1) ✅
- **Flow Status:** ON (1) ✅ *Nová aktivita!*
- **Flow Rate:** 18.8 l/min

### 🔧 Komponenty
- **Kompresor:** OFF (0)
- **Manual Defrost:** ON (1) ⚠️ *Aktivní!*
- **Backup heaters:** OFF (všechny)

## 📈 OČEKÁVANÉ ZMĚNY v 20:00

### 🌙 Silent Mode Activation
Očekávané změny za ~40 minut:
- **00003 Silent Mode Setting:** 0 → 1
- **10008 Silent Mode Status:** 0 → 1
- **Power consumption:** Možný pokles
- **Operation strategy:** Tišší provoz

### 📊 Monitoring Priority
1. **Silent mode transition** - přesný čas aktivace
2. **Power consumption changes** - vliv na spotřebu
3. **Temperature control** - jak moc se změní topení
4. **DHW management** - večerní ohřev před nocí

## 🎯 KLÍČOVÁ POZOROVÁNÍ

### ✅ Pozitivní
- Systém aktivně pracuje (pump ON, flow detection)
- Venkovní teplota vyšší = lepší efektivita
- Žádné chyby nebo alarmy
- Manual defrost možná kvuli údržbě

### ⚠️ K ověření
- **Manual Defrost ON** - proč je aktivní při 5°C?
- **DHW Target 23.5°C** - konečně rozumná hodnota!
- **Target Heating 19.4°C** - nižší než room temp?

## 🔮 Predikce na večer

Za 40 minut (20:00) očekávám:
1. **Silent mode aktivace** 🌙
2. **Možný ohřev DHW** na vyšší teplotu
3. **Gentle heating** room temperature
4. **Power consumption** optimization

---
**Status: Ready to monitor silent mode transition! 🌙**
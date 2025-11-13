# LG Therma V — Modbus/TCP Register Map & Home Assistant Integration

**Scope:** Consolidated reference for LG Therma V (PI‑485 gateway / RS‑485 → Modbus) when accessed via Modbus/TCP converter. Original **register names are preserved** (English), units and scaling included. Includes HA (Home Assistant) YAML, testing commands, and troubleshooting.

> Model families differ slightly. Always sanity‑check a few key registers (outdoor temperature, operation mode) before wiring everything into dashboards.

---

## 1) Modbus Primer (function codes & addressing)

| Block | Meaning | Function code | Read/Write | Typical content |
|---|---|---:|---:|---|
| **Holding Registers (30001+)** | Telemetry values | **0x03** (Read Holding Registers) | R | Water temps, flow, outdoor temp, product info, etc. |
| **Input Registers (40001+)** | Target/config read‑backs | **0x04** (Read Input Registers) | R (read‑only) | Operation mode, control method, target temps, energy state input |
| **Discrete Inputs (10001+)** | Boolean status | **0x02** (Read Discrete Inputs) | R | Pump/compressor/defrost/DHW/etc. |
| **Coils (00001+)** | Boolean controls | **0x01** (Read Coils), **0x05/0x0F** (Write) | R/W | Enable heating/cooling, enable DHW, silent mode, disinfection, emergency stop/op. |

### Addressing note (very important)
Many UIs are **1‑based** in manuals, while libraries (incl. Home Assistant) use **0‑based register addressing**.  
Example: manual register **30003** ⇒ HA `address: 2`.

---

## 2) Register Map (original names)

### 2.1 Holding Registers (0x03) — 30001+ (R)
> All temps are `0.1 °C × 10` unless noted. Flow is `0.1 LPM × 10`.

| Register | Name | Unit / Scaling | Notes |
|---:|---|---|---|
| 30001 | **Error Code** | — | Error code integer |
| 30002 | **ODU operation Cycle** | 0: Standby(OFF) / 1: Cooling / 2: Heating | Outdoor unit cycle |
| 30003 | **Water inlet temp.** | 0.1 °C ×10 | |
| 30004 | **Water outlet temp.** | 0.1 °C ×10 | |
| 30005 | **Backup heater outlet temp.** | 0.1 °C ×10 | |
| 30006 | **DHW tank water temp.** | 0.1 °C ×10 | |
| 30007 | **Solar collector temp.** | 0.1 °C ×10 | |
| 30008 | **Room air temp. (Circuit 1)** | 0.1 °C ×10 | |
| 30009 | **Current Flow rate** | 0.1 LPM ×10 | |
| 30010 | **Flow temp. (Circuit 2)** | 0.1 °C ×10 | |
| 30011 | **Room air temp. (Circuit 2)** | 0.1 °C ×10 | |
| 30012 | **Energy State input** | 0..n | External energy state input (see 40010 reference) |
| 30013 | **Outdoor Air temp.** | 0.1 °C ×10 | |
| 39998 | **Product Group** | 0x8X | 0x80, 0x83, 0x88, 0x89 |
| 39999 | **Product Info.** | enum | Split: 0 / Monobloc: 3 / High Temp: 4 / Medium Temp: 5 / System Boiler: 6 |

### 2.2 Input Registers (0x04) — 40001+ (R, read‑only)
| Register | Name | Values / Scaling |
|---:|---|---|
| 40001 | **Operation Mode** | 0: Cooling / 4: Heating / 3: Auto |
| 40002 | **Control method (Circuit 1/2)** | 0: Water outlet temp. control / 1: Water inlet temp. control / 2: Room air control |
| 40003 | **Target temp (Heating/Cooling) Circuit 1** | 0.1 °C ×10 |
| 40004 | **Room Air Temp. Circuit 1** | 0.1 °C ×10 |
| 40005 | **Shift value(Target) in auto mode Circuit 1** | 1K |
| 40006 | **Target temp (Heating/Cooling) Circuit 2** | 0.1 °C ×10 |
| 40007 | **Room Air Temp. Circuit 2** | 0.1 °C ×10 |
| 40008 | **Shift value(Target) in auto mode Circuit 2** | 1K |
| 40009 | **DHW Target temp.** | 0.1 °C ×10 |
| 40010 | **Energy state input** | 0: Not Use / 1: Forced off / 2: Normal op / 3: On‑recommendation / 4: On‑command step 1 / 5: On‑command step 2 / 6: On‑recommendation step 1 / 7: Energy Saving / 8: Super Energy saving |

### 2.3 Discrete Inputs (0x02) — 10001+ (R)
| Register | Name | 0/1 meaning |
|---:|---|---|
| 10001 | **Water flow status** | 0: Flow ok / 1: Flow too low |
| 10002 | **Water Pump status** | 0: OFF / 1: ON |
| 10003 | **Ext. Water Pump status** | 0: OFF / 1: ON |
| 10004 | **Compressor status** | 0: OFF / 1: ON |
| 10005 | **Defrosting status** | 0: OFF / 1: ON |
| 10006 | **DHW heating status** | 0: inactive / 1: active |
| 10007 | **DHW Tank disinfection status** | 0: inactive / 1: active |
| 10008 | **Silent mode status** | 0: inactive / 1: active |
| 10009 | **Cooling status** | 0: no cooling / 1: cooling |
| 10010 | **Solar pump status** | 0: OFF / 1: ON |
| 10011 | **Backup heater (Step 1) status** | 0: OFF / 1: ON |
| 10012 | **Backup heater (Step 2) status** | 0: OFF / 1: ON |
| 10013 | **DHW boost heater status** | 0: OFF / 1: ON |
| 10014 | **Error status** | 0: no error / 1: error |
| 10015 | **Emergency Operation Available (Space)** | 0: Unavailable / 1: Available |
| 10016 | **Emergency Operation Available (DHW)** | 0: Unavailable / 1: Available |
| 10017 | **Mix pump status** | 0: OFF / 1: ON |

### 2.4 Coils (0x01) — 00001+ (R/W)
| Coil | Name | Write values |
|---:|---|---|
| 00001 | **Enable/Disable (Heating/Cooling)** | 0: OFF / 1: ON |
| 00002 | **Enable/Disable (DHW)** | 0: OFF / 1: ON |
| 00003 | **Silent mode set** | 0: OFF / 1: ON |
| 00004 | **Start disinfection operation** | 0: Keep / 1: Start |
| 00005 | **Emergency stop** | 0: Normal / 1: E‑Stop |
| 00006 | **Start emergency operation** | 0: Keep / 1: Start |

---

## 3) Home Assistant (HA) — Modbus YAML

Below uses a TCP gateway at `192.168.100.199:502`, **Unit ID = 1**, and 0‑based addresses.

```yaml
modbus:
  - name: therma_v
    type: tcp
    host: 192.168.100.199
    port: 502
    timeout: 3
    retries: 3

    # --- Holding (300xx) ---
    sensors:
      - name: "LG Water inlet temp"
        slave: 1
        address: 2        # 30003
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Water outlet temp"
        slave: 1
        address: 3        # 30004
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG DHW tank water temp"
        slave: 1
        address: 5        # 30006
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Room air temp (Circuit 1)"
        slave: 1
        address: 7        # 30008
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Current Flow rate"
        slave: 1
        address: 8        # 30009
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "l/min"

      - name: "LG Flow temp (Circuit 2)"
        slave: 1
        address: 9        # 30010
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Room air temp (Circuit 2)"
        slave: 1
        address: 10       # 30011
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Outdoor Air temp"
        slave: 1
        address: 12       # 30013
        input_type: holding
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Product Group"
        slave: 1
        address: 39997    # 39998
        input_type: holding
        data_type: uint16

      - name: "LG Product Info"
        slave: 1
        address: 39998    # 39999
        input_type: holding
        data_type: uint16

    # --- Input (400xx) ---
  - name: therma_v_inputs
    type: tcp
    host: 192.168.100.199
    port: 502
    timeout: 3
    retries: 3
    sensors:
      - name: "LG Operation Mode"
        slave: 1
        address: 0        # 40001
        input_type: input
        data_type: uint16

      - name: "LG Control method (Circuit 1/2)"
        slave: 1
        address: 1        # 40002
        input_type: input
        data_type: uint16

      - name: "LG Target temp Circuit 1"
        slave: 1
        address: 2        # 40003
        input_type: input
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Target temp Circuit 2"
        slave: 1
        address: 5        # 40006
        input_type: input
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG DHW Target temp"
        slave: 1
        address: 8        # 40009
        input_type: input
        data_type: int16
        scale: 0.1
        precision: 1
        unit_of_measurement: "°C"

      - name: "LG Energy state input"
        slave: 1
        address: 9        # 40010
        input_type: input
        data_type: uint16

    # --- Discrete Inputs (100xx) ---
  - name: therma_v_status
    type: tcp
    host: 192.168.100.199
    port: 502
    timeout: 3
    retries: 3
    binary_sensors:
      - name: "LG Water flow status"
        slave: 1
        address: 0        # 10001
        input_type: discrete_input
      - name: "LG Water Pump status"
        slave: 1
        address: 1        # 10002
        input_type: discrete_input
      - name: "LG Compressor status"
        slave: 1
        address: 3        # 10004
        input_type: discrete_input
      - name: "LG Defrosting status"
        slave: 1
        address: 4        # 10005
        input_type: discrete_input
      - name: "LG DHW heating status"
        slave: 1
        address: 5        # 10006
        input_type: discrete_input
      - name: "LG Error status"
        slave: 1
        address: 13       # 10014
        input_type: discrete_input

    # --- Coils (000xx) ---
  - name: therma_v_ctrl
    type: tcp
    host: 192.168.100.199
    port: 502
    timeout: 3
    retries: 3
    switches:
      - name: "LG Enable Heating/Cooling"
        slave: 1
        address: 0        # 00001
        input_type: coil
      - name: "LG Enable DHW"
        slave: 1
        address: 1        # 00002
        input_type: coil
      - name: "LG Silent mode set"
        slave: 1
        address: 2        # 00003
        input_type: coil
      - name: "LG Start disinfection operation"
        slave: 1
        address: 3        # 00004
        input_type: coil
      - name: "LG Emergency stop"
        slave: 1
        address: 4        # 00005
        input_type: coil
      - name: "LG Start emergency operation"
        slave: 1
        address: 5        # 00006
        input_type: coil
```

### Optional: templates for friendly text
```yaml
template:
  - sensor:
      - name: "LG Operation Mode (text)"
        state: >
          {% set v = states('sensor.lg_operation_mode')|int(-1) %}
          {% if v == 0 %}Cooling{% elif v == 4 %}Heating{% elif v == 3 %}Auto{% else %}Unknown ({{v}}){% endif %}
```

---

## 4) Testing with `mbpoll`

Assuming TCP gateway at `192.168.100.199:502`, **Unit ID 1**:

- **Holding (0x03)** — read Outdoor Air temp (30013):
```bash
mbpoll -m tcp -a 1 -r 13 -c 1 -t 3:hex 192.168.100.199    # raw
mbpoll -m tcp -a 1 -r 13 -c 1 -t 3:int 192.168.100.199    # int (expects ×10)
```
- **Input (0x04)** — read Operation Mode (40001):
```bash
mbpoll -m tcp -a 1 -r 1 -c 1 -t 4:uint 192.168.100.199
```
- **Discrete Inputs (0x02)** — read Water flow status (10001):
```bash
mbpoll -m tcp -a 1 -r 1 -c 1 -t 2 192.168.100.199
```
- **Coils (0x01)** — read & write Enable DHW (00002):
```bash
mbpoll -m tcp -a 1 -r 2 -c 1 -t 0 192.168.100.199          # read
mbpoll -m tcp -a 1 -r 2 -0 192.168.100.199                 # write 0
mbpoll -m tcp -a 1 -r 2 -1 192.168.100.199                 # write 1
```

> `-t` types: `3` = holding, `4` = input, `2` = discrete inputs, `0` = coils.  
> For scaled values, divide by 10 in your head or script.

---

## 5) Troubleshooting & Tips

- **Address off by one?** Try shifting ±1. If one value matches (e.g., Outdoor temp), the rest are linear.
- **Time‑outs:** verify TCP converter in **TCP server** mode on port 502; Modbus/RTU side: 9600/8N1 per LG PI‑485 default (unless you changed it).
- **Unit ID:** must match your PI‑485 setting (commonly `1`). Wrong ID ⇒ timeouts.
- **Endian/word order:** These registers are **16‑bit**. For 32‑bit values (not in this sheet), mind word order (`int32`, `uint32`, `float32` with endian setting).
- **Write paths:** 400xx here are **read‑only** via Modbus. For control, use **coils (000xx)**. Some firmwares expose writable hold‑regs for setpoints—check your exact manual if you need write‑setpoints via 0x06/0x10.
- **HA polling rate:** default is fine. If bus is slow, add `scan_interval:` on noisy sensors.

---

## 6) Quick HA Address Reference

| Manual Reg. | HA `address` | Block |
|---:|---:|---|
| 30003 | 2 | holding |
| 30004 | 3 | holding |
| 30006 | 5 | holding |
| 30008 | 7 | holding |
| 30009 | 8 | holding |
| 30010 | 9 | holding |
| 30011 | 10 | holding |
| 30013 | 12 | holding |
| 39998 | 39997 | holding |
| 39999 | 39998 | holding |
| 40001 | 0 | input |
| 40002 | 1 | input |
| 40003 | 2 | input |
| 40006 | 5 | input |
| 40009 | 8 | input |
| 40010 | 9 | input |
| 10001 | 0 | discrete_input |
| 10002 | 1 | discrete_input |
| 10004 | 3 | discrete_input |
| 10005 | 4 | discrete_input |
| 10006 | 5 | discrete_input |
| 10014 | 13 | discrete_input |
| 00001 | 0 | coil |
| 00002 | 1 | coil |
| 00003 | 2 | coil |
| 00004 | 3 | coil |
| 00005 | 4 | coil |
| 00006 | 5 | coil |

---

## 7) Changelog (keep expanding in your repo)

- **v1.0** — Initial consolidated map (holding/input/discrete/coils), HA YAML, `mbpoll` cheat‑sheet, and troubleshooting.



**********************
Coil Register (0x01),,,,,
Register,Homeassistant,Description,Value Explanation,LG Doc,Remarks
00001,0,Enable/Disable (Heating/Cooling),0: Operation OFF / 1: Operation ON,TRUE,
00002,1,Enable/Disable (DHW),0: Operation OFF / 1: Operation ON,TRUE,
00003,2,Silent Mode Setting,0: Silent mode OFF / 1: Silent mode ON,TRUE,
00004,3,Start Disinfection Operation,0: Keep status / 1: Start operation,TRUE,
00005,4,Emergency Stop,0: Normal operation / 1: Emergency stop,TRUE,
00006,5,Start Emergency Operation,0: Keep status / 1: Start operation,TRUE,
,,,,,
Discrete Input Register (0x02),,,,,
Register,Homeassistant,Description,Value Explanation,LG Doc,Remarks
10001,0,Water Flow Status,0: Flow rate OK / 1: Flow rate too low,TRUE,
10002,1,Water Pump Status,0: Water pump OFF / 1: Water pump ON,TRUE,
10003,2,External Water Pump Status,0: Water pump OFF / 1: Water pump ON,TRUE,
10004,3,Compressor Status,0: Compressor OFF / 1: Compressor ON,TRUE,
10005,4,Defrosting Status,0: Defrost OFF / 1: Defrost ON,TRUE,
10006,5,DHW Heating Status,0: DHW inactive / 1: DHW active,TRUE,
10007,6,DHW Tank Disinfection Status,0: Disinfection inactive / 1: Disinfection active,TRUE,
10008,7,Silent Mode Status,0: Silent mode inactive / 1: Silent mode active,TRUE,
10009,8,Cooling Status,0: No cooling / 1: Cooling operation,TRUE,
10010,9,Solar Pump Status,0: Solar pump OFF / 1: Solar pump ON,TRUE,
10011,10,Backup Heater Status (Step 1),0: OFF / 1: ON,TRUE,
10012,11,Backup Heater Status (Step 2),0: OFF / 1: ON,TRUE,
10013,12,DHW Boost Heater Status,0: OFF / 1: ON,TRUE,
10014,13,Error Status,0: No error / 1: Error status,TRUE,
10015,14,Emergency Operation Available (Space Heating/Cooling),0: Not available / 1: Available,TRUE,
10016,15,Emergency Operation Available (DHW),0: Not available / 1: Available,TRUE,
10017,16,Mix Pump Status,0: Mix pump OFF / 1: Mix pump ON,TRUE,
,,,,,
Input Register (0x04),,,,,LG Doc: Holding Register (0x03)
Register,Homeassistant,Description,Value Explanation,LG Doc,Remarks
30001,0,Error Code,Error code,TRUE,
30002,1,ODU Operation Cycle,0: Standby (OFF) / 1: Cooling / 2: Heating,TRUE,
30003,2,Water Inlet Temperature,[0.1 °C ×10],TRUE,
30004,3,Water Outlet Temperature,[0.1 °C ×10],TRUE,
30005,4,Backup Heater Outlet Temperature,[0.1 °C ×10],TRUE,
30006,5,DHW Tank Water Temperature,[0.1 °C ×10],TRUE,
30007,6,Solar Collector Temperature,[0.1 °C ×10],TRUE,
30008,7,Room Air Temperature (Circuit 1),[0.1 °C ×10],TRUE,
30009,8,Current Flow Rate,[0.1 l/min ×10],TRUE,
30010,9,Flow Temperature (Circuit 2),[0.1 °C ×10],TRUE,
30011,10,Room Air Temperature (Circuit 2),[0.1 °C ×10],TRUE,
30012,11,Energy State Input,"0: Energy state 0, 1: Energy state 1...",TRUE,
30013,12,Outdoor Air Temperature,[0.1 °C ×10],TRUE,
30017,16,Liquid Gas Temperature,[0.1 °C ×1],FALSE,
30019,18,Suction Temperature,[0.1 °C ×1],FALSE,
30020,19,Hot Gas Temperature,[0.1 °C ×1],FALSE,
30021,20,Vapor Temperature Before Evaporator,[0.1 °C ×1],FALSE,
30022,21,Vapor Temperature After Evaporator,[0.1 °C ×1],FALSE,
30023,22,Vapor Pressure Condenser,[0.1 °C ×1],FALSE,
30024,23,Vapor Pressure Condenser,[0.1 °C ×1],FALSE,
30025,24,Compressor Speed,[Hz],TRUE,not available with software version 3.0.6.7a
39998,39997,Product Group,"0x8X (0x80, 0x83, 0x88, 0x89)",TRUE,
39999,39998,Product Info,"Split: 0, Monoblock: 3, High Temp: 4, Medium Temp: 5, System Boiler: 6",TRUE,
,,,,,
"Holding Register (0x03), for Write Command (0x06)",,,,,LG Doc: Input Register (0x04)
Register,Homeassistant,Description,Value Explanation,LG Doc,Remarks
40001,0,Operation Mode (Circuit 1/2),0: Cooling / 4: Heating / 3: Auto,TRUE,
40002,1,Control Method (Circuit 1/2),"0: Water outlet temp control, 1: Water inlet temp control, 2: Room air control",TRUE,
40003,2,Target Temperature (Heating/Cooling) Circuit 1,[0.1 °C ×10],TRUE,
40004,3,Room Air Temperature Circuit 1,[0.1 °C ×10],TRUE,
40005,4,Shift Value (Target) in Auto Mode Circuit 1,1K,TRUE,
40006,5,Target Temperature (Heating/Cooling) Circuit 2,[0.1 °C ×10],TRUE,
40007,6,Room Air Temperature Circuit 2,[0.1 °C ×10],TRUE,
40008,7,Shift Value (Target) in Auto Mode Circuit 2,1K,TRUE,
40009,8,DHW Target Temperature,[0.1 °C ×10],TRUE,
40010,9,Energy State Input,"0: Not use, 1: Forced off, 2: Normal operation, 3: On-recommendation, 4: On-command, 5: On-command Step 2, 6: On-recommendation Step 1, 7: Energy saving mode, 8: Super energy saving mode",TRUE,Evaluated via template sensor
49999,9998,Product Info,,TRUE,
,,,,,
Settings,Baudrate,9600bps,,,
,Stop-Bit,1,,,
,Parity,None,,,
,,,,,
,,,,,
,,Heating Circuit 1,,,
,,Heating Circuit 2,,,
,,DHW,,,
#!/usr/bin/env python3
"""
Jednoduché čtení Modbus TCP registrů - čistý TCP socket bez závislostí
Použití: python modbus_tcp.py <IP> <registr> [interval] [timeout]

Příklady:
    python modbus_tcp.py 192.168.100.199 30004        # Jednorázové čtení
    python modbus_tcp.py 192.168.100.199 30003 5      # Každých 5s
    python modbus_tcp.py 192.168.100.199 40018 2 1000 # Každé 2s s timeoutem 1s
"""

import sys
import socket
import struct
import time
from datetime import datetime

# Mapování registrů
REGISTRY = {
    30001: {"func": 3, "addr": 0,   "scale": 1,      "unit": "",      "name": "Error Code"},
    30002: {"func": 3, "addr": 1,   "scale": 1,      "unit": "",      "name": "Operation Cycle"},
    30003: {"func": 3, "addr": 2,   "scale": 0.1,    "unit": "°C",    "name": "Inlet Temperature"},
    30004: {"func": 3, "addr": 3,   "scale": 0.1,    "unit": "°C",    "name": "Outlet Temperature"},
    30005: {"func": 3, "addr": 4,   "scale": 0.1,    "unit": "°C",    "name": "DHW Circuit"},
    30006: {"func": 3, "addr": 5,   "scale": 0.1,    "unit": "°C",    "name": "DHW Tank"},
    30008: {"func": 3, "addr": 7,   "scale": 0.1,    "unit": "°C",    "name": "Room Temperature"},
    30009: {"func": 3, "addr": 8,   "scale": 0.055,  "unit": "l/min", "name": "Water Flow"},
    30013: {"func": 3, "addr": 12,  "scale": 0.1,    "unit": "°C",    "name": "Outdoor Temperature"},
    40001: {"func": 4, "addr": 0,   "scale": 1,      "unit": "",      "name": "Operation Mode"},
    40003: {"func": 4, "addr": 2,   "scale": 0.1,    "unit": "°C",    "name": "Target Temp Circuit 1"},
    40009: {"func": 4, "addr": 8,   "scale": 0.1,    "unit": "°C",    "name": "DHW Target Temp"},
    40013: {"func": 4, "addr": 12,  "scale": 0.018,  "unit": "bar",   "name": "Water Pressure"},
    40018: {"func": 4, "addr": 17,  "scale": 0.00479, "unit": "kW",   "name": "Electrical Power"},
}

def read_modbus_register(ip, reg_info, timeout_sec=1.0):
    """
    Přečte registr přes čistý TCP socket
    
    Args:
        ip: IP adresa Modbus serveru
        reg_info: Informace o registru (func, addr, scale, unit, name)
        timeout_sec: Timeout v sekundách
    
    Returns:
        tuple: (raw_value, scaled_value, success)
    """
    try:
        # TCP připojení
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)
        sock.connect((ip, 502))
        
        # Modbus TCP frame
        # Transaction ID (2B) + Protocol ID (2B) + Length (2B) + Unit ID (1B) + Function (1B) + Address (2B) + Count (2B)
        transaction_id = 1
        protocol_id = 0
        length = 6
        unit_id = 1
        function = reg_info["func"]
        address = reg_info["addr"]
        count = 1
        
        # Sestavení dotazu (big endian)
        query = struct.pack(">HHHBBHH", 
                           transaction_id, protocol_id, length, 
                           unit_id, function, address, count)
        
        # Odeslání
        sock.send(query)
        
        # Čtení odpovědi
        response = sock.recv(256)
        sock.close()
        
        # Dekódování odpovědi (Modbus TCP response format)
        if len(response) >= 9:
            # Skip header (6 bytes) + unit (1) + function (1) + byte count (1) = 9 bytes
            raw_value = struct.unpack(">H", response[9:11])[0]  # big endian uint16
            
            # Zpracování signed hodnot
            if raw_value > 32767:
                raw_value = raw_value - 65536
                
            scaled_value = raw_value * reg_info["scale"]
            return raw_value, scaled_value, True
        else:
            return None, None, False
            
    except Exception as e:
        return None, None, False

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nDostupné registry:")
        for reg in sorted(REGISTRY.keys()):
            info = REGISTRY[reg]
            print(f"  {reg:5d} - {info['name']}")
        sys.exit(1)
    
    # Parsování argumentů
    try:
        ip = sys.argv[1]
        register = int(sys.argv[2])
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        timeout_ms = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
        timeout_sec = timeout_ms / 1000.0
    except (ValueError, IndexError):
        print("Chyba: Neplatné parametry")
        sys.exit(1)
    
    # Kontrola registru
    if register not in REGISTRY:
        print(f"❌ Neznámý registr {register}")
        print("Dostupné registry:")
        for reg in sorted(REGISTRY.keys()):
            info = REGISTRY[reg]
            print(f"  {reg:5d} - {info['name']}")
        sys.exit(1)
    
    reg_info = REGISTRY[register]
    
    print(f"🔄 Čtu registr {register} ({reg_info['name']}) z {ip}")
    print(f"⏱️  Interval: {interval}s, Timeout: {timeout_ms}ms")
    print(f"⏹️  Zastavení: Ctrl+C\n")
    
    # Hlavní smyčka
    try:
        while True:
            timestamp = datetime.now().strftime("%H:%M:%S")
            raw, value, success = read_modbus_register(ip, reg_info, timeout_sec)
            
            if success:
                print(f"{timestamp}  raw={raw:4d}  value={value:.3f}{reg_info['unit']}")
            else:
                print(f"{timestamp}  ❌ CHYBA: Čtení selhalo")
            
            if interval <= 0:  # Jednorázové čtení
                break
                
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n✅ Ukončeno uživatelem")
    except Exception as e:
        print(f"\n❌ Neočekávaná chyba: {e}")

if __name__ == "__main__":
    main()
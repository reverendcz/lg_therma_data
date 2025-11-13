#!/usr/bin/env python3
"""
LG Therma V Modbus Scanner

Nástroj pro čtení registrů LG Therma V přes Modbus/TCP,
validaci (holding vs input), škálování a logování do CSV.
"""

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException


def convert_register_to_address(reg: int) -> int:
    """
    Převede "lidský" registr na 0-based address pro pymodbus.
    
    Args:
        reg: Registr (např. 30003, 40001)
    
    Returns:
        0-based address pro pymodbus
    """
    if 30001 <= reg <= 39999:  # Holding registers
        return reg - 30001
    elif 40001 <= reg <= 49999:  # Input registers
        return reg - 40001
    elif 10001 <= reg <= 19999:  # Discrete inputs
        return reg - 10001
    elif 1 <= reg <= 9999:  # Coils
        return reg - 1
    else:
        raise ValueError(f"Neplatný registr: {reg}")


def read_register_value(client: ModbusTcpClient, register_config: Dict, unit: int) -> Dict:
    """
    Přečte hodnotu z jednoho registru s podporou 'auto' módu.
    
    Args:
        client: Modbus client
        register_config: Konfigurace registru
        unit: Unit ID
    
    Returns:
        Slovník s výsledky čtení
    """
    reg = register_config['reg']
    name = register_config['name']
    table = register_config['table']
    scale = register_config['scale']
    unit_str = register_config['unit']
    
    address = convert_register_to_address(reg)
    
    result = {
        'name': name,
        'reg': reg,
        'address0': address,
        'table': table,
        'raw': None,
        'scaled': None,
        'unit': unit_str,
        'ok': False,
        'error': ''
    }
    
    try:
        if table == 'holding':
            response = client.read_holding_registers(address, 1, slave=unit)
        elif table == 'input':
            response = client.read_input_registers(address, 1, slave=unit)
        elif table == 'auto':
            # Preferuj holding, pokud vrátí chybu nebo 0, zkus input
            try:
                response = client.read_holding_registers(address, 1, slave=unit)
                if response.isError() or (hasattr(response, 'registers') and response.registers[0] == 0):
                    # Zkus input registry
                    response_input = client.read_input_registers(address, 1, slave=unit)
                    if not response_input.isError() and hasattr(response_input, 'registers') and response_input.registers[0] != 0:
                        response = response_input
                        result['table'] = 'input'  # Aktualizuj skutečně použitou tabulku
                    else:
                        result['table'] = 'holding'  # Zůstaň u holding i když je 0
                else:
                    result['table'] = 'holding'
            except Exception:
                # Pokud holding selže, zkus input
                response = client.read_input_registers(address, 1, slave=unit)
                result['table'] = 'input'
        else:
            raise ValueError(f"Nepodporovaná tabulka: {table}")
        
        if response.isError():
            result['error'] = f"Modbus error: {response}"
            return result
        
        if not hasattr(response, 'registers') or len(response.registers) == 0:
            result['error'] = "Žádná data v odpovědi"
            return result
        
        raw_value = response.registers[0]
        
        # Převod na signed int16 pokud je hodnota > 32767
        if raw_value > 32767:
            raw_value = raw_value - 65536
        
        result['raw'] = raw_value
        result['scaled'] = raw_value * scale
        result['ok'] = True
        
    except ModbusException as e:
        result['error'] = f"Modbus exception: {e}"
    except Exception as e:
        result['error'] = f"Chyba: {e}"
    
    return result


def load_config(config_file: Path) -> Dict:
    """Načte konfiguraci z YAML souboru."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Chyba při načítání konfigurace: {e}", file=sys.stderr)
        sys.exit(1)


def write_csv_header(csv_file: Path) -> None:
    """Zapíše hlavičku CSV souboru."""
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ts', 'name', 'reg', 'address0', 'table', 'raw', 'scaled', 'unit', 'ok', 'error'])


def write_csv_row(csv_file: Path, result: Dict) -> None:
    """Zapíše řádek do CSV souboru."""
    timestamp = datetime.now().isoformat()
    
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            timestamp,
            result['name'],
            result['reg'],
            result['address0'],
            result['table'],
            result['raw'],
            result['scaled'],
            result['unit'],
            result['ok'],
            result['error']
        ])


def scan_registers(config: Dict, csv_file: Path, once: bool = False) -> None:
    """
    Hlavní funkce pro skenování registrů.
    
    Args:
        config: Načtená konfigurace
        csv_file: Cesta k CSV souboru
        once: Pokud True, provede pouze jeden průchod
    """
    connection = config['connection']
    registers = config['registers']
    
    # Připojení k Modbus
    client = ModbusTcpClient(
        host=connection['host'],
        port=connection['port'],
        timeout=connection['timeout']
    )
    
    try:
        if not client.connect():
            print(f"Nelze se připojit k {connection['host']}:{connection['port']}", file=sys.stderr)
            sys.exit(2)
        
        print(f"Připojen k {connection['host']}:{connection['port']}")
        
        # Zkontroluj, zda existuje CSV soubor a případně vytvoř hlavičku
        if not csv_file.exists():
            write_csv_header(csv_file)
            print(f"Vytvořen CSV soubor: {csv_file}")
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- Iterace {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            for i, register_config in enumerate(registers):
                try:
                    result = read_register_value(client, register_config, connection['unit'])
                    
                    # Výpis na konzoli
                    if result['ok']:
                        print(f"✓ {result['name']}: {result['scaled']:.1f} {result['unit']} "
                              f"(raw: {result['raw']}, table: {result['table']})")
                    else:
                        print(f"✗ {result['name']}: {result['error']}")
                    
                    # Zápis do CSV
                    write_csv_row(csv_file, result)
                    
                    # Delay mezi dotazy (kromě posledního)
                    if i < len(registers) - 1:
                        time.sleep(connection['delay_ms'] / 1000.0)
                        
                except Exception as e:
                    print(f"✗ Chyba při čtení {register_config.get('name', 'N/A')}: {e}")
                    # Zapíš chybový záznam do CSV
                    error_result = {
                        'name': register_config.get('name', 'N/A'),
                        'reg': register_config.get('reg', 0),
                        'address0': 0,
                        'table': register_config.get('table', 'unknown'),
                        'raw': None,
                        'scaled': None,
                        'unit': register_config.get('unit', ''),
                        'ok': False,
                        'error': str(e)
                    }
                    write_csv_row(csv_file, error_result)
            
            if once:
                break
            
            # Čekání do další iterace není potřeba pokud máme delay_ms mezi registry
            print(f"Dokončena iterace {iteration}")
            
    except KeyboardInterrupt:
        print("\nUkončuji na požádání uživatele...")
    except Exception as e:
        print(f"Kritická chyba: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        client.close()
        print("Odpojeno od Modbus serveru")


def main():
    """Hlavní funkce programu."""
    parser = argparse.ArgumentParser(
        description="LG Therma V Modbus Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Příklady použití:
  python lgscan.py --once --yaml registers.yaml --out scan.csv
  python lgscan.py --interval 10 --yaml registers.yaml --out scan.csv
        """
    )
    
    parser.add_argument('--once', action='store_true',
                       help='Provede pouze jeden průchod')
    parser.add_argument('--interval', type=int, default=60,
                       help='Interval mezi průchody v sekundách (default: 60)')
    parser.add_argument('--yaml', type=Path, default='registers.yaml',
                       help='Cesta ke konfiguračnímu YAML souboru')
    parser.add_argument('--out', type=Path, default='scan.csv',
                       help='Výstupní CSV soubor')
    
    args = parser.parse_args()
    
    # Kontrola existence konfiguračního souboru
    if not args.yaml.exists():
        print(f"Konfigurační soubor neexistuje: {args.yaml}", file=sys.stderr)
        sys.exit(1)
    
    # Načti konfiguraci
    config = load_config(args.yaml)
    
    # Validace konfigurace
    required_keys = ['connection', 'registers']
    for key in required_keys:
        if key not in config:
            print(f"Chybí klíč v konfiguraci: {key}", file=sys.stderr)
            sys.exit(1)
    
    required_conn_keys = ['host', 'port', 'unit', 'timeout', 'delay_ms']
    for key in required_conn_keys:
        if key not in config['connection']:
            print(f"Chybí klíč v connection: {key}", file=sys.stderr)
            sys.exit(1)
    
    if not config['registers']:
        print("Žádné registry k načtení", file=sys.stderr)
        sys.exit(1)
    
    # Spusť skenování
    if args.once:
        print("Režim: Jeden průchod")
        scan_registers(config, args.out, once=True)
    else:
        print(f"Režim: Kontinuální s intervalem {args.interval}s")
        while True:
            scan_registers(config, args.out, once=True)
            if args.interval > 0:
                print(f"Čekám {args.interval} sekund do další iterace...")
                time.sleep(args.interval)


if __name__ == '__main__':
    main()
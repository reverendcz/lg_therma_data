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


# ANSI barevné kódy pro terminal output
class Colors:
    # Základní barvy
    RED = '\033[91m'
    GREEN = '\033[92m' 
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Světlejší varianty
    BRIGHT_RED = '\033[91;1m'
    BRIGHT_GREEN = '\033[92;1m'
    BRIGHT_YELLOW = '\033[93;1m'
    BRIGHT_BLUE = '\033[94;1m'
    BRIGHT_MAGENTA = '\033[95;1m'
    BRIGHT_CYAN = '\033[96;1m'
    
    # Reset
    RESET = '\033[0m'
    BOLD = '\033[1m'


def colorize_delta(delta_str: str, is_binary: bool = False, is_temperature: bool = False, 
                  is_power: bool = False, is_flow: bool = False) -> str:
    """
    Přidá barevné zvýraznění k delta stringu podle typu hodnoty.
    
    Args:
        delta_str: String s delta změnou
        is_binary: True pro binární hodnoty (0→1)
        is_temperature: True pro teploty
        is_power: True pro energie/výkon  
        is_flow: True pro průtok
    
    Returns:
        Barevně zvýrazněný delta string
    """
    if not delta_str:
        return delta_str
        
    if is_binary:
        # Binární změny - zelená pro 0→1, červená pro 1→0
        if "0→1" in delta_str:
            return f"{Colors.BRIGHT_GREEN}{delta_str}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_RED}{delta_str}{Colors.RESET}"
    elif is_temperature:
        # Teploty - červená pro nárůst, modrá pro pokles
        if "🔥" in delta_str:
            return f"{Colors.BRIGHT_RED}{delta_str}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_BLUE}{delta_str}{Colors.RESET}"
    elif is_power:
        # Energie - žlutá pro nárůst, fialová pro pokles
        if "⬆️" in delta_str:
            return f"{Colors.BRIGHT_YELLOW}{delta_str}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_MAGENTA}{delta_str}{Colors.RESET}"
    elif is_flow:
        # Průtok - cyan pro nárůst, bílá pro pokles
        if "💪" in delta_str:
            return f"{Colors.BRIGHT_CYAN}{delta_str}{Colors.RESET}"
        else:
            return f"{Colors.WHITE}{delta_str}{Colors.RESET}"
    else:
        # Obecné hodnoty - zelená pro nárůst, červená pro pokles
        if "📈" in delta_str:
            return f"{Colors.BRIGHT_GREEN}{delta_str}{Colors.RESET}"
        else:
            return f"{Colors.BRIGHT_RED}{delta_str}{Colors.RESET}"


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
            response = client.read_holding_registers(address, count=1, slave=unit)
        elif table == 'input':
            response = client.read_input_registers(address, count=1, slave=unit)
        elif table == 'discrete':
            response = client.read_discrete_inputs(address, count=1, slave=unit)
        elif table == 'coils':
            response = client.read_coils(address, count=1, slave=unit)
        elif table == 'auto':
            # Preferuj holding, pokud vrátí chybu nebo 0, zkus input
            try:
                response = client.read_holding_registers(address, count=1, slave=unit)
                if response.isError() or (hasattr(response, 'registers') and response.registers[0] == 0):
                    # Zkus input registry
                    response_input = client.read_input_registers(address, count=1, slave=unit)
                    if not response_input.isError() and hasattr(response_input, 'registers') and response_input.registers[0] != 0:
                        response = response_input
                        result['table'] = 'input'  # Aktualizuj skutečně použitou tabulku
                    else:
                        result['table'] = 'holding'  # Zůstaň u holding i když je 0
                else:
                    result['table'] = 'holding'
            except Exception:
                # Pokud holding selže, zkus input
                response = client.read_input_registers(address, count=1, slave=unit)
                result['table'] = 'input'
        else:
            raise ValueError(f"Nepodporovaná tabulka: {table}")
        
        if response.isError():
            result['error'] = f"Modbus error: {response}"
            return result
        
        # Pro discrete inputs a coils použij bits místo registers
        if table in ['discrete', 'coils']:
            if not hasattr(response, 'bits') or len(response.bits) == 0:
                result['error'] = "Žádná data v odpovědi"
                return result
            raw_value = 1 if response.bits[0] else 0
        else:
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


def calculate_cop(results: Dict[int, Dict]) -> Optional[float]:
    """
    Vypočítá COP (Coefficient of Performance) na základě aktuálních hodnot.
    
    COP = Tepelný výkon / Elektrický příkon
    
    Pro odhad tepelného výkonu používáme:
    Q = ṁ × cp × ΔT
    kde:
    - ṁ = hmotnostní tok vody [kg/s] 
    - cp = specifické teplo vody ≈ 4.18 kJ/(kg·K)
    - ΔT = rozdíl teplot výstup - vstup [K]
    
    Args:
        results: Dictionary s výsledky čtení registrů (klíč = reg number)
    
    Returns:
        COP hodnota nebo None pokud nelze vypočítat
    """
    try:
        # Potřebné registry pro COP výpočet
        flow_rate_reg = 30009      # Průtok [l/min]
        outlet_temp_reg = 30004    # Výstupní teplota [°C]  
        inlet_temp_reg = 30003     # Vstupní teplota [°C]
        power_reg = 40018          # Elektrický příkon [kW]
        
        # Kontrola dostupnosti všech potřebných hodnot
        required_regs = [flow_rate_reg, outlet_temp_reg, inlet_temp_reg, power_reg]
        for reg in required_regs:
            if reg not in results or not results[reg]['ok']:
                return None
                
        # Extrakce hodnot
        flow_rate = results[flow_rate_reg]['scaled']      # l/min
        outlet_temp = results[outlet_temp_reg]['scaled']  # °C
        inlet_temp = results[inlet_temp_reg]['scaled']    # °C  
        electrical_power = results[power_reg]['scaled']   # kW
        
        # Kontrola platnosti hodnot
        if flow_rate <= 0 or electrical_power <= 0:
            return None
            
        # Výpočet tepelného rozdílu
        delta_temp = outlet_temp - inlet_temp  # K (Kelvin rozdíl = Celsius rozdíl)
        
        # Pokud není tepelný spád, COP není relevantní (sníženo z 0.1 na 0.05)
        if abs(delta_temp) < 0.05:
            return None
            
        # Konverze průtoku na kg/s (1 l/min = 1 kg/min při 20°C)
        mass_flow = flow_rate / 60.0  # kg/s
        
        # Tepelný výkon [kW]
        # Q = ṁ × cp × ΔT
        # cp vody ≈ 4.18 kJ/(kg·K) = 4.18 kW·s/(kg·K)
        thermal_power = mass_flow * 4.18 * abs(delta_temp)  # kW
        
        # COP výpočet
        cop = thermal_power / electrical_power
        
        # Rozumné limity pro COP (0.1 - 25.0) 
        if 0.1 <= cop <= 25.0:
            return cop
        else:
            return None
            
    except Exception:
        return None


def write_csv_header(csv_file: Path) -> None:
    """Zapíše hlavičku CSV souboru."""
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['ts', 'name', 'reg', 'address0', 'table', 'raw', 'scaled', 'unit', 'delta', 'previous_value', 'ok', 'error', 'cop'])


def write_csv_row(csv_file: Path, result: Dict, cop_value: Optional[float] = None) -> None:
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
            result.get('delta', ''),
            result.get('previous_value', ''),
            result['ok'],
            result['error'],
            f"{cop_value:.2f}" if cop_value is not None else ""
        ])


def scan_registers(config: Dict, csv_file: Path, once: bool = False, interval: int = 60, log_file: Path = None) -> None:
    """
    Hlavní funkce pro skenování registrů.
    
    Args:
        config: Načtená konfigurace
        csv_file: Cesta k CSV souboru
        once: Pokud True, provede pouze jeden průchod
        interval: Interval mezi iteracemi v sekundách
        log_file: Cesta k log souboru (volitelné)
    """
    connection = config['connection']
    registers = config['registers']
    
    # Dictionary pro sledování posledních hodnot (delta monitoring)
    last_values = {}
    
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
        
        connection_msg = f"Připojen k {connection['host']}:{connection['port']}"
        print(connection_msg)
        
        # Logování do souboru pokud je specifikováno
        if log_file:
            with open(log_file, 'a', encoding='utf-8') as lf:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                lf.write(f"[{timestamp}] === LG THERMA V SCAN START ===\n")
                lf.write(f"[{timestamp}] {connection_msg}\n")
        
        # Zkontroluj, zda existuje CSV soubor a případně vytvoř hlavičku
        if not csv_file.exists():
            write_csv_header(csv_file)
            csv_msg = f"Vytvořen CSV soubor: {csv_file}"
            print(csv_msg)
            
            # Logování do souboru
            if log_file:
                with open(log_file, 'a', encoding='utf-8') as lf:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    lf.write(f"[{timestamp}] {csv_msg}\n")
        
        iteration = 0
        while True:
            iteration += 1
            iteration_header = f"\n--- Iterace {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
            print(iteration_header)
            
            # Logování hlavičky iterace do souboru
            if log_file:
                with open(log_file, 'a', encoding='utf-8') as lf:
                    lf.write(f"{iteration_header}\n")
            
            # Dictionary pro ukládání všech výsledků iterace (pro COP výpočet)
            iteration_results = {}
            
            for i, register_config in enumerate(registers):
                try:
                    result = read_register_value(client, register_config, connection['unit'])
                    
                    # Uložení výsledku pro COP výpočet
                    if result['ok']:
                        iteration_results[result['reg']] = result
                    
                    # Delta monitoring - výpočet změny oproti poslednímu stavu
                    delta_str = ""
                    delta_value = ""
                    previous_val = ""
                    reg_key = result['reg']
                    
                    if result['ok'] and reg_key in last_values:
                        current_val = result['scaled']
                        last_val = last_values[reg_key]
                        previous_val = last_val
                        
                        if current_val != last_val:
                            # Detekuj typ hodnoty podle jednotky a rozsahu
                            is_binary = (current_val in [0.0, 1.0] and last_val in [0.0, 1.0])
                            is_temperature = "°C" in result['unit']
                            is_flow = "l/min" in result['unit'] 
                            is_power = ("kW" in result['unit'] or "W" in result['unit'])
                            
                            if is_binary:
                                # Binární hodnoty: 0→1 nebo 1→0
                                delta_str = f" 📈({last_val:.0f}→{current_val:.0f})"
                                delta_value = f"{last_val:.0f}→{current_val:.0f}"
                            else:
                                # Číselné hodnoty s delta a směr
                                delta = current_val - last_val
                                if abs(delta) >= 0.01:  # Snížený práh pro citlivější detekci změn
                                    if is_temperature:
                                        delta_sign = "🔥" if delta > 0 else "❄️"
                                        delta_str = f" {delta_sign}({delta:+.1f}°C)"
                                        delta_value = f"{delta:+.1f}°C"
                                    elif is_power:
                                        delta_sign = "⬆️" if delta > 0 else "⬇️"
                                        unit_suffix = "kW" if "kW" in result['unit'] else "W"
                                        format_str = "{:+.1f}" if "kW" in result['unit'] else "{:+.0f}"
                                        delta_str = f" {delta_sign}({format_str.format(delta)}{unit_suffix})"
                                        delta_value = f"{format_str.format(delta)}{unit_suffix}"
                                    elif is_flow:
                                        delta_sign = "💪" if delta > 0 else "💧"
                                        delta_str = f" {delta_sign}({delta:+.1f}l/min)"
                                        delta_value = f"{delta:+.1f}l/min"
                                    else:
                                        delta_sign = "📈" if delta > 0 else "📉"
                                        delta_str = f" {delta_sign}({delta:+.1f})"
                                        delta_value = f"{delta:+.1f}"
                    
                    # Přidání delta informací do result pro CSV a log
                    result['delta'] = delta_value
                    result['previous_value'] = previous_val
                    
                    # Uložení aktuální hodnoty pro příští iteraci
                    if result['ok']:
                        last_values[reg_key] = result['scaled']
                    
                    # Výpis na konzoli s delta informací
                    if result['ok']:
                        # Detekuj typ hodnoty pro barevné zvýraznění
                        is_binary = (result['scaled'] in [0.0, 1.0]) and delta_value and "→" in delta_value
                        is_temperature = "°C" in result['unit']
                        is_flow = "l/min" in result['unit']
                        is_power = ("kW" in result['unit'] or "W" in result['unit'])
                        
                        # Aplikuj barevné zvýraznění na delta_str
                        colored_delta_str = colorize_delta(delta_str, is_binary, is_temperature, is_power, is_flow)
                        
                        output_line = f"✓ [{result['reg']:05d}] {result['name']}: {result['scaled']:.1f} {result['unit']}{colored_delta_str} (raw: {result['raw']}, table: {result['table']})"
                        print(output_line)
                        
                        # Pro log soubor používáme nebarevnou verzi
                        log_line = f"✓ [{result['reg']:05d}] {result['name']}: {result['scaled']:.1f} {result['unit']}{delta_str} (raw: {result['raw']}, table: {result['table']})"
                    else:
                        output_line = f"✗ [{result['reg']:05d}] {result['name']}: {result['error']}"
                        log_line = output_line
                        print(output_line)
                    
                    # Logování do souboru pokud je specifikováno (bez barev)
                    if log_file:
                        with open(log_file, 'a', encoding='utf-8') as lf:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            lf.write(f"[{timestamp}] {log_line}\n")
                    
                    # Delay mezi dotazy (kromě posledního)
                    if i < len(registers) - 1:
                        time.sleep(connection['delay_ms'] / 1000.0)
                        
                except Exception as e:
                    error_line = f"✗ [{register_config.get('reg', 0):05d}] Chyba při čtení {register_config.get('name', 'N/A')}: {e.__class__.__name__}: {e}"
                    print(error_line)
                    
                    # Logování chyby do souboru pokud je specifikováno
                    if log_file:
                        with open(log_file, 'a', encoding='utf-8') as lf:
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            lf.write(f"[{timestamp}] {error_line}\n")
                    
                    # Zapíš chybový záznam do CSV
                    error_result = {
                        'name': register_config.get('name', 'N/A'),
                        'reg': register_config.get('reg', 0),
                        'address0': 0,
                        'table': register_config.get('table', 'unknown'),
                        'raw': None,
                        'scaled': None,
                        'unit': register_config.get('unit', ''),
                        'delta': '',
                        'previous_value': '',
                        'ok': False,
                        'error': str(e)
                    }
                    write_csv_row(csv_file, error_result)
            
            # COP výpočet na konci iterace
            cop_value = calculate_cop(iteration_results)
            
            # Výpis COP informací
            if cop_value is not None:
                cop_output = f"🔥 COP (Coefficient of Performance): {cop_value:.2f}"
                print(cop_output)
                
                # Logování COP do souboru
                if log_file:
                    with open(log_file, 'a', encoding='utf-8') as lf:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        lf.write(f"[{timestamp}] {cop_output}\n")
            else:
                cop_info = "ℹ️  COP: Nedostatečný tepelný spád nebo chybné hodnoty"
                print(cop_info)
                
                if log_file:
                    with open(log_file, 'a', encoding='utf-8') as lf:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        lf.write(f"[{timestamp}] {cop_info}\n")
            
            # Zápis všech výsledků do CSV s COP hodnotou
            for result in iteration_results.values():
                write_csv_row(csv_file, result, cop_value)
            
            if once:
                break
            
            # Dokončení iterace
            print(f"Dokončena iterace {iteration}")
            
            # Čekání do další iterace
            if interval > 0:
                print(f"Čekám {interval} sekund do další iterace...")
                time.sleep(interval)
            
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
    parser.add_argument('--log', type=Path, default=None,
                       help='Výstupní log soubor (volitelné)')
    
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
        scan_registers(config, args.out, once=True, log_file=args.log)
    else:
        print(f"Režim: Kontinuální s intervalem {args.interval}s")
        scan_registers(config, args.out, once=False, interval=args.interval, log_file=args.log)


if __name__ == '__main__':
    main()
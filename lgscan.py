#!/usr/bin/env python3
"""
LG Therma V Modbus Scanner

Nástroj pro čtení registrů LG Therma V přes Modbus/TCP,
validaci (holding vs input), škálování a logování do CSV.
"""

__version__ = "1.0.0"
__author__ = "reverendcz"
__date__ = "2025-11-17"

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# Try to import colorama for Windows color support
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # Auto-reset colors
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback - no colors
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


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
        reg: Registr (např. 30003, 40001, 50001)
    
    Returns:
        0-based address pro pymodbus
    """
    if 30001 <= reg <= 39999:  # Input registers 30xxx
        return reg - 30001
    elif 40001 <= reg <= 49999:  # Holding registers 40xxx
        return reg - 40001
    elif 50001 <= reg <= 59999:  # Extended registers 50xxx (input/holding based on table type)
        return reg - 50001
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
        elif table == 'coils' or table == 'coil':
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
    
    ⚠️ DŮLEŽITÉ: COP se počítá JEN pokud:
    - Běží kompresor (Compressor Status = 1)
    - Neběží defrost (Defrosting Status = 0)
    - Je topný režim (Operation Cycle = 2 = Heating)
    
    Pro odhad tepelného výkonu používáme:
    Q = ṁ × cp × ΔT
    kde:
    - ṁ = hmotnostní tok vody [kg/s] 
    - cp = specifické teplo vody ≈ 4.18 kJ/(kg·K)
    - ΔT = rozdíl teplot výstup - vstup [K]
    
    Args:
        results: Dictionary s výsledky čtení registrů (klíč = reg number)
    
    Returns:
        COP hodnota nebo None pokud nelze vypočítat nebo podmínky nejsou splněny
    """
    try:
        # Potřebné registry pro COP výpočet
        flow_rate_reg = 30009      # Průtok [l/min]
        outlet_temp_reg = 30004    # Výstupní teplota [°C]  
        inlet_temp_reg = 30003     # Vstupní teplota [°C]
        power_reg = 40018          # Elektrický příkon [kW]
        
        # Registry pro kontrolu stavu
        compressor_reg = 10004     # Compressor Status (1 = běží)
        defrost_reg = 10005        # Defrosting Status (0 = neběží defrost)
        operation_reg = 30002      # Operation Cycle (2 = Heating)
        
        # Kontrola dostupnosti všech potřebných hodnot
        required_regs = [flow_rate_reg, outlet_temp_reg, inlet_temp_reg, power_reg]
        status_regs = [compressor_reg, defrost_reg, operation_reg]
        
        for reg in required_regs:
            if reg not in results or not results[reg]['ok']:
                return None
                
        # Kontrola stavových registrů (nemusí být všechny dostupné)
        for reg in status_regs:
            if reg not in results or not results[reg]['ok']:
                print(f"⚠️ COP: Stavový registr {reg} nedostupný, počítám COP bez kontroly stavu")
                break
        else:
            # Všechny stavové registry jsou dostupné - kontrolujeme podmínky
            compressor_status = results[compressor_reg]['scaled'] if compressor_reg in results else 0
            defrost_status = results[defrost_reg]['scaled'] if defrost_reg in results else 0
            operation_status = results[operation_reg]['scaled'] if operation_reg in results else 2
            
            # COP má smysl počítat JEN když:
            if compressor_status != 1:
                print(f"🚫 COP: Kompresor neběží (status: {compressor_status})")
                return None
            if defrost_status != 0:
                print(f"🚫 COP: Běží defrost (status: {defrost_status})")
                return None
            if operation_status != 2:
                print(f"🚫 COP: Není topný režim (operation: {operation_status})")
                return None
            
            print(f"✅ COP: Podmínky splněny - kompresor běží, defrost neběží, topí se")
                
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
                                delta_str = f" ({delta:+.1f}°C)"
                                delta_value = f"{delta:+.1f}°C"
                            elif is_power:
                                unit_suffix = "kW" if "kW" in result['unit'] else "W"
                                format_str = "{:+.2f}" if "kW" in result['unit'] else "{:+.0f}"
                                delta_str = f" ({format_str.format(delta)}{unit_suffix})"
                                delta_value = f"{format_str.format(delta)}{unit_suffix}"
                            elif is_flow:
                                delta_str = f" ({delta:+.1f}l/min)"
                                delta_value = f"{delta:+.1f}l/min"
                            else:
                                delta_str = f" ({delta:+.1f})"
                                delta_value = f"{delta:+.1f}"                    # Přidání delta informací do result pro CSV a log
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
                        
                        output_line = f"✓ [{result['reg']:05d}] {result['name']}: {result['scaled']:.2f} {result['unit']}{colored_delta_str} (raw: {result['raw']}, table: {result['table']})"
                        print(output_line)
                        
                        # Pro log soubor používáme nebarevnou verzi
                        log_line = f"✓ [{result['reg']:05d}] {result['name']}: {result['scaled']:.2f} {result['unit']}{delta_str} (raw: {result['raw']}, table: {result['table']})"
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


def clear_screen():
    """Vymaže obrazovku - Windows optimized"""
    if os.name == 'nt':  # Windows
        # Use ANSI escape codes for smoother clearing on Windows
        print('\033[2J\033[H', end='')
    else:  # Unix/Linux
        os.system('clear')


def get_color_for_value(register_data: Dict, value: Union[int, float, str]) -> tuple:
    """Vrátí barvu podle hodnoty a typu registru"""
    if not COLORAMA_AVAILABLE:
        return "", ""
    
    unit = register_data.get('unit', '')
    
    if unit == "°C":
        if isinstance(value, (int, float)):
            if value > 25:
                return Fore.RED, Style.BRIGHT
            elif value < 10:
                return Fore.BLUE, Style.BRIGHT
            else:
                return Fore.GREEN, ""
    elif unit == "kW":
        return Fore.YELLOW, Style.BRIGHT
    elif isinstance(value, str) and value in ["ON", "1"]:
        return Fore.GREEN, Style.BRIGHT
    elif unit in ["l/min", "bar"]:
        return Fore.CYAN, ""
    
    return Fore.WHITE, ""














def draw_table_header(title: str, iteration: int):
    """Vykreslí hlavičku tabulky"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_title = f"🏠 {title} - Iteration {iteration}"
    subtitle = f"📅 {timestamp} | 🖥️ Smooth Table Mode"
    
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 108}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{full_title.center(108)}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{subtitle.center(108)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 108}{Style.RESET_ALL}")
    
    header = f"{Fore.WHITE}{Style.BRIGHT}"
    print(f"{header}┌────────┬─────────────────────────────────────┬──────────┬────────┬──────┬──────────────────────┬────────────┐{Style.RESET_ALL}")
    print(f"{header}│Register│ Parameter                           │ Value    │ Unit   │ Raw  │ Delta Changes        │ Status     │{Style.RESET_ALL}")
    print(f"{header}├────────┼─────────────────────────────────────┼──────────┼────────┼──────┼──────────────────────┼────────────┤{Style.RESET_ALL}")


def draw_table_row(register_data: Dict, result: Dict, last_values: Dict = None):
    """Vykreslí jeden řádek tabulky s ultra-precízním zarovnáním a delta tracking"""
    reg_num = register_data.get('reg', 'N/A')
    name = register_data.get('name', 'Unknown')
    
    # Formátování registru - přidáme leading zeros pro coils
    if isinstance(reg_num, int):
        if reg_num < 10:  # Pro coils (1,2,3) zobrazit jako 00001, 00002, 00003
            reg_str = f"{reg_num:05d}"
        else:
            reg_str = str(reg_num)
    else:
        reg_str = str(reg_num)
    
    # Zkrátit jméno pokud je příliš dlouhé - JEDNODUCHÉ bez emoji
    display_name = name
    if len(display_name) > 33:
        display_name = display_name[:30] + "..."
    
    # Padding na presne 33 znakov
    display_name = f"{display_name:<33}"
    
    # Delta calculation
    delta_str = ""
    if result['ok'] and last_values is not None and reg_num in last_values:
        current_val = result['scaled']
        last_val = last_values[reg_num]
        
        if current_val != last_val:
            # Detekuj typ hodnoty podle jednotky a rozsahu
            is_binary = (current_val in [0.0, 1.0] and last_val in [0.0, 1.0])
            is_temperature = "°C" in register_data.get('unit', '')
            is_flow = "l/min" in register_data.get('unit', '') 
            is_power = ("kW" in register_data.get('unit', '') or "W" in register_data.get('unit', ''))
            
            if is_binary:
                delta_str = f"{last_val:.0f}→{current_val:.0f}"
            else:
                delta = current_val - last_val
                if abs(delta) >= 0.01:
                    if is_temperature:
                        delta_str = f"{delta:+.1f}°C"
                    elif is_power:
                        unit_suffix = "kW" if "kW" in register_data.get('unit', '') else "W"
                        format_str = "{:+.2f}" if "kW" in register_data.get('unit', '') else "{:+.0f}"
                        delta_str = f"{format_str.format(delta)}{unit_suffix}"
                    elif is_flow:
                        delta_str = f"{delta:+.1f}l/min"
                    else:
                        delta_str = f"{delta:+.1f}"
    
    if result['ok']:
        scaled_value = result['scaled']
        unit = register_data.get('unit', '')
        raw_value = result['raw']
        
        color, style = get_color_for_value(register_data, scaled_value)
        
        # ULTRA-PRESNÉ formátovanie s delta sloupcem
        reg_part = f"{reg_str:>8}"                        # Presne 8 znakov
        name_part = f" {display_name} "                   # Presne 37 znakov celkom
        
        # Value formatting
        if isinstance(scaled_value, float):
            value_part = f"{scaled_value:>10.2f}"
        elif isinstance(scaled_value, int):
            value_part = f"{scaled_value:>10d}"
        else:
            value_part = f"{str(scaled_value):>10}"
        
        unit_part = f" {unit:<6} "                        # Presne 8 znakov (s medzerami)
        raw_part = f"{raw_value:>6d}" if isinstance(raw_value, int) else f"{str(raw_value):>6}"
        # Fixní šířka delta sloupce - 21 znaků celkem
        if delta_str:
            delta_part = f" {delta_str:<20}"  # Vlevo zarovnaná delta + padding na 20 znaků
        else:
            delta_part = f" {'--':<20}"  # Konzistentní šířka
        status_part = " OK         "                          # Presne 12 znakov
        
        # Farby - aplikujú sa len na časti bez medziery
        if COLORAMA_AVAILABLE:
            reg_colored = f"{Fore.CYAN}{reg_part}{Style.RESET_ALL}"
            name_colored = f" {Fore.WHITE}{display_name}{Style.RESET_ALL} "
            value_colored = f"{color}{style}{value_part}{Style.RESET_ALL}"
            unit_colored = f" {Fore.YELLOW}{unit:<6}{Style.RESET_ALL} "
            raw_colored = f"{Fore.MAGENTA}{raw_part}{Style.RESET_ALL}"
            
            # Delta s farbami - FIXNÍ ŠÍŘKA 20 ZNAKŮ
            if delta_str:
                # Aplikuj barvy na samotný delta text
                colored_delta = colorize_delta(delta_str, is_binary=(scaled_value in [0.0, 1.0]), is_temperature=('°C' in unit))
                # Fixní padding - 20 mezer po colored textu
                spaces_needed = max(0, 20 - len(delta_str))
                delta_colored = f" {colored_delta}{' ' * spaces_needed}"
            else:
                delta_colored = f" {Fore.LIGHTBLACK_EX}{'--'}{' ' * 18}{Style.RESET_ALL}"
            
            status_colored = f" {Fore.GREEN}✅ OK{Style.RESET_ALL}       "
        else:
            reg_colored = reg_part
            name_colored = name_part
            value_colored = value_part
            unit_colored = unit_part
            raw_colored = raw_part
            delta_colored = delta_part
            status_colored = status_part
        
        # Fixed layout - každá časť má pevnú pozíciu
        line = f"│{reg_colored}│{name_colored}│{value_colored}│{unit_colored}│{raw_colored} │{delta_colored}│{status_colored}│"
        print(line)
        
    else:
        error_msg = result.get('error', 'Unknown error')[:10]
        
        # Error formatting
        reg_part = f"{reg_str:>8}"
        name_part = f" {display_name} "                   # display_name už má správnu šírku 35+2=37
        value_part = "     ERROR"
        unit_part = "        "                             # 8 medzier
        raw_part = " ERR "
        delta_part = f" {'--':<20}"                      # Konzistentní šířka 21 znaků
        status_part = " ERROR      "                           # 12 znakov
        
        if COLORAMA_AVAILABLE:
            reg_colored = f"{Fore.CYAN}{reg_part}{Style.RESET_ALL}"
            name_colored = f" {Fore.WHITE}{display_name}{Style.RESET_ALL} "
            value_colored = f"{Fore.RED}{value_part}{Style.RESET_ALL}"
            unit_colored = f"{Fore.YELLOW}      {Style.RESET_ALL}  "
            raw_colored = f"{Fore.MAGENTA}{raw_part}{Style.RESET_ALL}"
            delta_colored = f" {Fore.LIGHTBLACK_EX}{'--':<20}{Style.RESET_ALL}"
            status_colored = f" {Fore.RED}❌ ERR{Style.RESET_ALL}      "
        else:
            reg_colored = reg_part
            name_colored = name_part
            value_colored = value_part
            unit_colored = unit_part
            raw_colored = raw_part
            delta_colored = delta_part
            status_colored = status_part
        
        # Error line s delta sloupcem
        line = f"│{reg_colored}│{name_colored}│{value_colored}│{unit_colored}│{raw_colored} │{delta_colored}│{status_colored}│"
        print(line)


def draw_table_footer(cop_value: Optional[float], total_registers: int, successful: int):
    """Vykreslí patičku tabulky se statistikami"""
    print(f"{Fore.WHITE}{Style.BRIGHT}└────────┴─────────────────────────────────────┴──────────┴────────┴──────┴──────────────────────┴────────────┘{Style.RESET_ALL}")
    
    # Statistiky
    success_rate = (successful / total_registers * 100) if total_registers > 0 else 0
    cop_str = f"{cop_value:.2f}" if cop_value else "N/A"
    
    stats1 = f"🔥 COP: {cop_str} | 📊 Success: {successful}/{total_registers} ({success_rate:.1f}%)"
    stats2 = f"🎛️ Controls: Ctrl+C to quit | Auto refresh every few seconds"
    
    print(f"{Fore.GREEN}{Style.BRIGHT}{'─' * 108}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{stats1.center(108)}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{stats2.center(108)}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}{'─' * 108}{Style.RESET_ALL}")
    
    if not COLORAMA_AVAILABLE:
        print(f"\n{Fore.YELLOW}💡 Tip: Pro barvy nainstalujte colorama: pip install colorama{Style.RESET_ALL}")


def simple_monitor(config: Dict, interval: int, csv_file: Optional[Path] = None, 
                  log_file: Optional[Path] = None):
    """
    Jednoduchý monitoring režim - čistý textový výpis všech registrů najednou.
    """
    print("🖥️ Spouštím Simple Monitor...")
    print(f"📡 Připojuji k {config['connection']['host']}:{config['connection']['port']}")
    
    # Připojení k Modbus s delším timeout
    client = ModbusTcpClient(
        host=config['connection']['host'],
        port=config['connection']['port'],
        timeout=10  # Zvýšený timeout na 10 sekund
    )
    
    if not client.connect():
        print("❌ Připojení selhalo!")
        return
    
    print("✅ Připojen k Modbus serveru")
    print(f"📊 Celkem {len(config['registers'])} registrů")
    print("💡 Stiskněte Ctrl+C pro ukončení\n")
    
    # Vyčištění obrazovky jen jednou na začátku
    clear_screen()
    
    iteration = 0
    previous_values = {}  # Sledování předchozích hodnot pro delta
    
    try:
        while True:
            iteration += 1
            
            # ANSI pozicionování kurzoru na začátek (kromě první iterace)
            if iteration > 1:
                print("\033[2J\033[H", end="")  # Vymaž celou obrazovku + kurzor na pozíciu 0,0
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("🖥️ LG Therma V Simple Monitor")
            print("=" * 70)
            print(f"📅 {timestamp} | Iterace #{iteration}")
            print(f"📊 Celkem {len(config['registers'])} registrů")
            print("=" * 70)
            
            # Načti všechny registry
            results = []
            successful = 0
            iteration_results = {}
            
            for register_data in config['registers']:
                result = read_register_value(client, register_data, config['connection']['unit'])
                results.append((register_data, result))
                
                if result['ok']:
                    successful += 1
                    reg_num = register_data.get('reg')
                    iteration_results[reg_num] = result
            
            # COP výpočet
            cop_value = calculate_cop(iteration_results)
            
            # Výpis všech registrů najednou
            for register_data, result in results:
                reg_num = register_data.get('reg')
                name = register_data.get('name', 'Unknown')
                unit = register_data.get('unit', '')
                
                if result['ok']:
                    value = result['scaled']
                    
                    # Výpočet delta
                    delta_str = ""
                    if iteration > 1 and reg_num in previous_values:
                        prev_val = previous_values[reg_num]
                        if isinstance(value, (int, float)) and isinstance(prev_val, (int, float)):
                            delta = value - prev_val
                            if abs(delta) >= 0.1:
                                if delta > 0:
                                    delta_str = f" (+{delta:.1f})"
                                else:
                                    delta_str = f" ({delta:.1f})"
                        elif value != prev_val:
                            delta_str = " (změna)"
                    
                    # Formátování hodnoty
                    if isinstance(value, float):
                        value_str = f"{value:.2f}"
                    else:
                        value_str = str(value)
                    
                    # Výpis řádku s odsazením
                    if unit:
                        print(f"  {reg_num:>5}: {name:<40} {value_str:>10} {unit:<8}{delta_str}")
                    else:
                        print(f"  {reg_num:>5}: {name:<40} {value_str:>10}{delta_str}")
                    
                    # Uložit hodnotu pro příští iteraci
                    previous_values[reg_num] = value
                else:
                    print(f"  {reg_num:>5}: {name:<40} ERROR")
            
            # Statistiky
            print("=" * 70)
            success_rate = (successful / len(config['registers']) * 100) if len(config['registers']) > 0 else 0
            print(f"📊 Úspěšnost: {successful}/{len(config['registers'])} ({success_rate:.1f}%)")
            
            if cop_value:
                print(f"🔥 COP: {cop_value:.2f}")
            else:
                print("🔥 COP: N/A")
            
            # CSV zápis
            if csv_file:
                if iteration == 1:
                    write_csv_header(csv_file)
                for register_data, result in results:
                    write_csv_row(csv_file, result, cop_value)
            
            # Log zápis
            if log_file:
                write_results_to_log(results, log_file, iteration, cop_value)
            
            print(f"\n⏰ Další aktualizace za {interval}s | Ctrl+C pro ukončení")
            
            # Jednoduchý countdown
            for i in range(interval, 0, -1):
                print(f"\r⏳ Čekám {i}s...     ", end="", flush=True)
                time.sleep(1)
            print("\r" + " " * 20 + "\r", end="")  # Vymaž countdown
            
    except KeyboardInterrupt:
        print("\n\n✅ Simple Monitor ukončen uživatelem!")
    except Exception as e:
        print(f"\n❌ Chyba: {e}")
    finally:
        client.close()
        print("👋 Odpojeno od Modbus serveru")


def draw_simple_table_header(title: str, iteration: int):
    """Vykreslí hlavičku simple tabulky"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_title = f"🏠 {title} - Iteration {iteration}"
    subtitle = f"📅 {timestamp} | 🖥️ Simple Mode"
    
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 100}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{full_title.center(100)}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{subtitle.center(100)}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'═' * 100}{Style.RESET_ALL}")
    
    header = f"{Fore.WHITE}{Style.BRIGHT}"
    print(f"{header}┌────────┬─────────────────────────────────────┬──────────┬────────┬──────────┬────────────┐{Style.RESET_ALL}")
    print(f"{header}│Register│ Parameter                           │ Value    │ Unit   │ Delta    │ Status     │{Style.RESET_ALL}")
    print(f"{header}├────────┼─────────────────────────────────────┼──────────┼────────┼──────────┼────────────┤{Style.RESET_ALL}")


def draw_simple_table_row(register_data: Dict, result: Dict, previous_value=None):
    """Vykreslí jeden řádek simple tabulky"""
    reg_num = register_data.get('reg', 'N/A')
    name = register_data.get('name', 'Unknown')
    
    # Formátování registru
    if isinstance(reg_num, int):
        if reg_num < 10:
            reg_str = f"{reg_num:05d}"
        else:
            reg_str = str(reg_num)
    else:
        reg_str = str(reg_num)
    
    # Zkrátit jméno pokud je příliš dlouhé
    display_name = name
    if len(display_name) > 33:
        display_name = display_name[:30] + "..."
    
    display_name = f"{display_name:<33}"
    
    if result['ok']:
        scaled_value = result['scaled']
        unit = register_data.get('unit', '')
        
        color, style = get_color_for_value(register_data, scaled_value)
        
        # Výpočet delta
        delta_str = "    -    "
        if previous_value is not None:
            if isinstance(scaled_value, (int, float)) and isinstance(previous_value, (int, float)):
                delta = scaled_value - previous_value
                if abs(delta) >= 0.1:
                    if delta > 0:
                        delta_str = f"{delta:+7.1f}⬆"
                    else:
                        delta_str = f"{delta:+7.1f}⬇"
                else:
                    delta_str = "    =    "
            elif scaled_value != previous_value:
                delta_str = "  ZMĚNA "
        
        # Formátování částí
        reg_part = f"{reg_str:>8}"
        name_part = f" {display_name} "
        
        if isinstance(scaled_value, float):
            value_part = f"{scaled_value:>10.2f}"
        elif isinstance(scaled_value, int):
            value_part = f"{scaled_value:>10d}"
        else:
            value_part = f"{str(scaled_value):>10}"
        
        unit_part = f" {unit:<6} "
        delta_part = f"{delta_str:>10}"
        
        # Barvy
        if COLORAMA_AVAILABLE:
            reg_colored = f"{Fore.CYAN}{reg_part}{Style.RESET_ALL}"
            name_colored = f" {Fore.WHITE}{display_name}{Style.RESET_ALL} "
            value_colored = f"{color}{style}{value_part}{Style.RESET_ALL}"
            unit_colored = f" {Fore.YELLOW}{unit:<6}{Style.RESET_ALL} "
            
            # Delta barvy
            if "⬆" in delta_str:
                delta_colored = f" {Fore.GREEN}{delta_part}{Style.RESET_ALL}"
            elif "⬇" in delta_str:
                delta_colored = f" {Fore.RED}{delta_part}{Style.RESET_ALL}"
            else:
                delta_colored = f" {Fore.WHITE}{delta_part}{Style.RESET_ALL}"
            
            status_colored = f" {Fore.GREEN}✅ OK{Style.RESET_ALL}       "
        else:
            reg_colored = reg_part
            name_colored = name_part
            value_colored = value_part
            unit_colored = unit_part
            delta_colored = f" {delta_part}"
            status_colored = " OK         "
        
        line = f"│{reg_colored}│{name_colored}│{value_colored}│{unit_colored}│{delta_colored}│{status_colored}│"
        print(line)
        
    else:
        # Error formatting
        reg_part = f"{reg_str:>8}"
        name_part = f" {display_name} "
        value_part = "     ERROR"
        unit_part = "        "
        delta_part = "   ERR    "
        
        if COLORAMA_AVAILABLE:
            reg_colored = f"{Fore.CYAN}{reg_part}{Style.RESET_ALL}"
            name_colored = f" {Fore.WHITE}{display_name}{Style.RESET_ALL} "
            value_colored = f"{Fore.RED}{value_part}{Style.RESET_ALL}"
            unit_colored = f"{Fore.YELLOW}      {Style.RESET_ALL}  "
            delta_colored = f" {Fore.RED}{delta_part}{Style.RESET_ALL}"
            status_colored = f" {Fore.RED}❌ ERR{Style.RESET_ALL}   "
        else:
            reg_colored = reg_part
            name_colored = name_part
            value_colored = value_part
            unit_colored = unit_part
            delta_colored = f" {delta_part}"
            status_colored = " ERROR      "
        
        line = f"│{reg_colored}│{name_colored}│{value_colored}│{unit_colored}│{delta_colored}│{status_colored}│"
        print(line)


def draw_simple_table_footer(cop_value: Optional[float], total_registers: int, successful: int):
    """Vykreslí patičku simple tabulky"""
    print(f"{Fore.WHITE}{Style.BRIGHT}└────────┴─────────────────────────────────────┴──────────┴────────┴──────────┴────────────┘{Style.RESET_ALL}")
    
    # Statistiky
    success_rate = (successful / total_registers * 100) if total_registers > 0 else 0
    cop_str = f"{cop_value:.2f}" if cop_value else "N/A"
    
    stats1 = f"🔥 COP: {cop_str} | 📊 Success: {successful}/{total_registers} ({success_rate:.1f}%)"
    
    print(f"{Fore.GREEN}{Style.BRIGHT}{'─' * 100}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{stats1.center(100)}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{Style.BRIGHT}{'─' * 100}{Style.RESET_ALL}")


def simple_monitor_old(config: Dict, interval: int, csv_file: Optional[Path] = None, 
                  log_file: Optional[Path] = None):
    """
    Jednoduchý monitoring režim - zobrazuje jen hlavní hodnoty bez blikání.
    """
    print("🖥️ Spouštím Simple Monitor...")
    
    # Definice hlavních registrů k zobrazení
    main_registers = [
        30008,  # Room Temperature
        30004,  # Heating Circuit OUTLET  
        30003,  # Heating Circuit INLET
        30013,  # Outdoor Air Temperature
        30009,  # Water Flow Rate
        40018,  # Electrical Power Consumption
        40013,  # Water Pressure
    ]
    
    # Přidáme statusové registery pro COP kontrolu
    status_registers = [
        10004,  # Compressor Status
        10005,  # Defrosting Status  
        30002,  # Operation Cycle Status
    ]
    
    # Filtruj pouze hlavní registry + statusové
    main_filtered = [reg for reg in config['registers'] if reg.get('reg') in main_registers]
    status_filtered = [reg for reg in config['registers'] if reg.get('reg') in status_registers]
    print(f"📡 Připojuji k {config['connection']['host']}:{config['connection']['port']}")
    
    client = None
    try:
        client = ModbusTcpClient(
            host=config['connection']['host'],
            port=config['connection']['port'],
            timeout=config['connection']['timeout']
        )
        
        if not client.connect():
            print(f"❌ Nepodařilo se připojit k Modbus serveru", file=sys.stderr)
            return
            
        print("✅ Připojen k Modbus serveru")
        print("=" * 60)
        print("🏠 LG Therma V - Hlavní hodnoty")
        print("=" * 60)
        
        iteration = 0
        
        while True:
            iteration += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Vymazat předchozí výpis - jednodušší způsob
            if iteration > 1:
                print("\n" * 3)  # Jen několik prázdných řádků místo clear
                print("=" * 60)
                print("🏠 LG Therma V - Hlavní hodnoty")
                print("=" * 60)
            
            print(f"📅 {timestamp} | Iterace {iteration}")
            print("-" * 60)
            
            results = []
            cop_data = {}
            status_data = {}
            
            # Přečti všechny hlavní registry
            for register_data in main_filtered:
                result = read_register_value(client, register_data, config['connection']['unit'])
                results.append((register_data, result))
                
                if result['ok']:
                    # Uložit data pro COP výpočet
                    reg_num = register_data.get('reg')
                    if reg_num == 30004:  # Outlet temp
                        cop_data['outlet'] = result['scaled']
                    elif reg_num == 30003:  # Inlet temp
                        cop_data['inlet'] = result['scaled']
                    elif reg_num == 40018:  # Electrical power
                        cop_data['power'] = result['scaled']
                    elif reg_num == 30009:  # Water flow
                        cop_data['flow'] = result['scaled']
            
            # Přečti statusové registry (pro COP kontrolu)
            for register_data in status_filtered:
                result = read_register_value(client, register_data, config['connection']['unit'])
                if result['ok']:
                    reg_num = register_data.get('reg')
                    if reg_num == 10004:  # Compressor Status
                        status_data['compressor'] = result['scaled']
                    elif reg_num == 10005:  # Defrosting Status
                        status_data['defrost'] = result['scaled']
                    elif reg_num == 30002:  # Operation Cycle
                        status_data['operation'] = result['scaled']
            
            # Zobraz výsledky v jednoduchém formátu
            for register_data, result in results:
                name = register_data.get('name', 'Unknown')
                unit = register_data.get('unit', '')
                
                if result['ok']:
                    value = result['scaled']
                    if isinstance(value, float):
                        value_str = f"{value:.1f}"
                    else:
                        value_str = str(value)
                    
                    # Emoji podle typu
                    emoji = ""
                    if "Room" in name:
                        emoji = "🏠"
                    elif "OUTLET" in name:
                        emoji = "🔥"
                    elif "INLET" in name:
                        emoji = "🔄"
                    elif "Outdoor" in name:
                        emoji = "🌤️"
                    elif "Flow" in name:
                        emoji = "💧"
                    elif "Power" in name:
                        emoji = "⚡"
                    elif "Pressure" in name:
                        emoji = "💪"
                    
                    print(f"{emoji} {name}: {value_str} {unit}")
                else:
                    print(f"❌ {name}: ERROR")
            
            # Inteligentní COP výpočet s kontrolou stavu
            cop_calculated = False
            
            # Kontrola všech potřebných dat pro COP
            if all(key in cop_data for key in ['outlet', 'inlet', 'power']) and cop_data['power'] > 0.1:
                
                # Kontrola stavových podmínek
                can_calculate_cop = True
                status_info = []
                
                if 'compressor' in status_data:
                    if status_data['compressor'] != 1:
                        can_calculate_cop = False
                        status_info.append(f"kompresor neběží ({status_data['compressor']})")
                    else:
                        status_info.append("kompresor běží ✅")
                
                if 'defrost' in status_data:
                    if status_data['defrost'] != 0:
                        can_calculate_cop = False
                        status_info.append(f"běží defrost ({status_data['defrost']})")
                    else:
                        status_info.append("defrost neběží ✅")
                        
                if 'operation' in status_data:
                    if status_data['operation'] != 2:
                        can_calculate_cop = False
                        status_info.append(f"není topný režim ({status_data['operation']})")
                    else:
                        status_info.append("topný režim ✅")
                
                if can_calculate_cop:
                    temp_delta = abs(cop_data['outlet'] - cop_data['inlet'])
                    if temp_delta >= 0.05:
                        flow_rate = cop_data.get('flow', 27.5)  # Použij čtený průtok nebo default
                        thermal_power = flow_rate * 4.18 * temp_delta / 60  # kW
                        cop = max(0.1, min(25.0, thermal_power / cop_data['power']))
                        print(f"\n🔥 COP (Coefficient of Performance): {cop:.2f}")
                        if status_info:
                            print(f"📊 Status: {', '.join(status_info)}")
                        cop_calculated = True
                    else:
                        print(f"\n🚫 COP: Tepelný spád příliš malý ({temp_delta:.2f}°C)")
                else:
                    print(f"\n🚫 COP nelze počítat: {', '.join(status_info)}")
            
            if not cop_calculated and not status_data:
                print(f"\n⚠️ COP: Stavové registry nedostupné, nelze ověřit podmínky")
            
            print("-" * 60)
            print(f"⏰ Další aktualizace za {interval}s | Ctrl+C pro ukončení")
            
            # CSV zápis (pokud je požadován)
            if csv_file and iteration == 1:
                write_csv_header(csv_file)
            
            if csv_file:
                for register_data, result in results:
                    write_csv_row(csv_file, result, cop_data.get('cop'))
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n✅ Simple Monitor ukončen uživatelem!")
        print("👋 Děkujeme za použití!")
    except Exception as e:
        print(f"\n❌ Chyba: {e}")
    finally:
        if client:
            client.close()


def write_results_to_log(results: List[tuple], log_file: Path, iteration: int, cop_value: Optional[float]):
    """Zapíše výsledky do log souboru"""
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n--- Table Monitor Iteration {iteration} - {datetime.now().isoformat()} ---\n")
        if cop_value:
            f.write(f"COP: {cop_value:.2f}\n")
        
        for register_data, result in results:
            reg_num = register_data.get('reg', 'N/A')
            name = register_data.get('name', 'Unknown')
            if result['ok']:
                scaled_value = result['scaled']
                unit = register_data.get('unit', '')
                f.write(f"✓ [{reg_num}] {name}: {scaled_value} {unit}\n")
            else:
                f.write(f"✗ [{reg_num}] {name}: ERROR - {result.get('error', 'Unknown')}\n")


def smooth_table_monitor(config: Dict, interval: int, csv_file: Optional[Path] = None, 
                        log_file: Optional[Path] = None):
    """
    Monitoring v režimu plynulé tabulky bez blikání.
    Používá buffer rendering pro okamžité zobrazení.
    """
    print(f"🖥️ Spouštím Smooth Table Monitor (buffer rendering)...")
    print(f"📡 Připojuji k {config['connection']['host']}:{config['connection']['port']}")
    
    if COLORAMA_AVAILABLE:
        print(f"{Fore.GREEN}✅ Colorama dostupná - plné barevné zobrazení{Style.RESET_ALL}")
    else:
        print(f"{Fore.YELLOW}⚠️  Colorama není dostupná - bez barev{Style.RESET_ALL}")

    # Připojení k Modbus
    client = ModbusTcpClient(
        host=config['connection']['host'],
        port=config['connection']['port'],
        timeout=config['connection']['timeout']
    )
    
    if not client.connect():
        print(f"{Fore.RED}❌ Připojení selhalo!{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}✅ Připojen k Modbus serveru{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}🚀 Spouštím plynulý monitoring...{Style.RESET_ALL}")
    print(f"{Fore.BLUE}💡 Stiskněte Ctrl+C pro ukončení{Style.RESET_ALL}")
    # Odebráno time.sleep(2) pro rychlejší start
    
    # Vyčištění obrazovky jen jednou na začátku
    import os
    os.system('cls' if os.name == 'nt' else 'clear')
    
    iteration = 0
    first_run = True
    last_values = {}  # Delta tracking pro smooth mode
    
    try:
        while True:
            iteration += 1
            
            # ANSI pozicionování kurzoru - optimalizované pro snížení blikání
            if not first_run:
                # Vymaž pouze progress řádek a přeskoč na začátek
                print("\r\033[K", end="")  # Vymaže aktuální řádek
                print("\033[H", end="")    # Kurzor na pozici 0,0
            
            # Načti všetky data najprv (bez vykreslovanja)
            results = []
            successful = 0
            iteration_results = {}
            
            # Načítaj všetky registre do pamäte
            for register_data in config['registers']:
                result = read_register_value(client, register_data, config['connection']['unit'])
                results.append((register_data, result))
                
                if result['ok']:
                    successful += 1
                    reg_num = register_data.get('reg')
                    iteration_results[reg_num] = result
            
            # COP výpočet
            cop_value = calculate_cop(iteration_results)
            
            # Teraz vykresli kompletnu tabulku naraz
            # Header
            draw_table_header("LG Therma V Smooth Monitor", iteration)
            
            # Všetky data riadky naraz s delta tracking
            for register_data, result in results:
                draw_table_row(register_data, result, last_values)
            
            # Footer
            draw_table_footer(cop_value, len(config['registers']), successful)
            
            # Status řádek
            status_color = Fore.GREEN if cop_value else Fore.YELLOW
            cop_text = f"{cop_value:.2f}" if cop_value else "N/A"
            print(f"{status_color}🔥 COP: {cop_text} | 📊 Úspěšnost: {successful}/{len(config['registers'])} | ⏰ Iteration: {iteration}{Style.RESET_ALL}")
            
            # CSV zápis
            if csv_file:
                if iteration == 1:
                    write_csv_header(csv_file)
                for register_data, result in results:
                    write_csv_row(csv_file, result, cop_value)
            
            # Log zápis
            if log_file:
                write_results_to_log(results, log_file, iteration, cop_value)
            
            # Update last_values pro delta tracking
            for register_data, result in results:
                if result['ok']:
                    reg_num = register_data.get('reg')
                    last_values[reg_num] = result['scaled']
            
            first_run = False
            
            # Čekání s optimalizovaným progress indikátorem
            for i in range(0, interval, 2):  # Progress co 2 sekundy
                remaining = interval - i
                if remaining > 0:
                    progress_filled = min(interval - remaining, interval)
                    progress_empty = max(0, interval - progress_filled)
                    progress = "⏳ Aktualizace za " + "█" * progress_filled + "░" * progress_empty + f" {remaining}s"
                    print(f'\r{Fore.BLUE}{progress}{Style.RESET_ALL}', end='', flush=True)
                    time.sleep(min(2, remaining))  # Čekej max 2 sekundy
            
            # Vymaž progress řádek - optimalizované
            print(f'\r{" " * 80}\r', end='', flush=True)
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.GREEN}✅ Smooth Monitor ukončen uživatelem!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}📊 Celkem iterací: {iteration}{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Chyba: {e}{Style.RESET_ALL}")
    finally:
        client.close()
        print(f"{Fore.BLUE}👋 Odpojeno od Modbus serveru{Style.RESET_ALL}")


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
    
    parser.add_argument('--version', action='version', 
                       version=f'LG Therma V Monitor v{__version__}')
    parser.add_argument('--once', action='store_true',
                       help='Provede pouze jeden průchod')
    parser.add_argument('--interval', type=int, default=10,
                       help='Interval mezi průchody v sekundách (default: 10)')
    parser.add_argument('--smooth', action='store_true',
                       help='Zobrazí data v plynulé tabulce bez blikání (doporučeno)')
    parser.add_argument('--simple', action='store_true',
                       help='Zobrazí pouze hlavní hodnoty (teploty, průtok, spotřeba)')
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
    if args.smooth:
        print("Režim: Plynulá tabulka (bez blikání)")
        if args.once:
            print("⚠️ --once je ignorován v smooth režimu")
        smooth_table_monitor(config, args.interval, args.out, args.log)
    elif args.simple:
        print("Režim: Jednoduché zobrazení")
        if args.once:
            print("⚠️ --once je ignorován v simple režimu")
        simple_monitor(config, args.interval, args.out, args.log)
    elif args.once:
        print("Režim: Jeden průchod")
        scan_registers(config, args.out, once=True, log_file=args.log)
    else:
        print(f"Režim: Kontinuální s intervalem {args.interval}s")
        scan_registers(config, args.out, once=False, interval=args.interval, log_file=args.log)


if __name__ == '__main__':
    main()
"""CLI nástroj pro čtení registrů LG Therma V pomocí Modbus/TCP."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException


@dataclass
class ConnectionConfig:
    """Parametry Modbus TCP klienta."""

    host: str = "192.168.100.199"
    port: int = 502
    unit: int = 1
    timeout: float = 2.0
    delay_ms: int = 120


@dataclass
class RegisterConfig:
    """Definice jednoho Modbus registru."""

    name: str
    reg: int
    table: str
    scale: float = 1.0
    unit: str = ""


CSV_FIELDS = [
    "ts",
    "name",
    "reg",
    "address0",
    "table",
    "raw",
    "scaled",
    "unit",
    "ok",
    "error",
]


def load_config(path: Path) -> Tuple[ConnectionConfig, List[RegisterConfig]]:
    """Načte YAML konfiguraci a vrátí ji jako datové třídy."""

    if not path.exists():
        raise FileNotFoundError(f"Konfigurační soubor '{path}' neexistuje")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    connection_data: Dict[str, Any] = data.get("connection", {}) or {}
    defaults = ConnectionConfig()
    connection = ConnectionConfig(
        host=str(connection_data.get("host", defaults.host)),
        port=int(connection_data.get("port", defaults.port)),
        unit=int(connection_data.get("unit", defaults.unit)),
        timeout=float(connection_data.get("timeout", defaults.timeout)),
        delay_ms=int(connection_data.get("delay_ms", defaults.delay_ms)),
    )

    registers_data = data.get("registers")
    if not registers_data:
        raise ValueError("V konfiguraci chybí sekce 'registers'.")

    registers: List[RegisterConfig] = []
    for entry in registers_data:
        try:
            name = str(entry["name"])
            reg = int(entry["reg"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Každá položka musí mít 'name' a číselný 'reg'.") from exc

        table = str(entry.get("table", "holding")).lower()
        if table not in {"holding", "input", "auto"}:
            raise ValueError(f"Neznámý typ tabulky '{table}' pro registr {name}.")

        scale = float(entry.get("scale", 1.0))
        unit = str(entry.get("unit", ""))
        registers.append(RegisterConfig(name=name, reg=reg, table=table, scale=scale, unit=unit))

    return connection, registers


def register_to_address(register_number: int) -> int:
    """Převede „lidské“ číslo registru na 0-based offset.

    Např. 30003 -> 2. Používáme první cifru pro určení začátku tabulky.
    """

    if 1 <= register_number <= 9999:
        base = 1
    elif 10001 <= register_number <= 19999:
        base = 10001
    elif 30001 <= register_number <= 39999:
        base = 30001
    elif 40001 <= register_number <= 49999:
        base = 40001
    else:
        raise ValueError(f"Registr {register_number} nelze převést na adresu.")

    return register_number - base


def read_single_table(
    client: ModbusTcpClient, table: str, address: int, unit: int
) -> Tuple[Optional[int], Optional[str]]:
    """Načte jeden registr z dané tabulky a vrátí hodnotu nebo chybu."""

    try:
        if table == "holding":
            response = client.read_holding_registers(address=address, count=1, unit=unit)
        elif table == "input":
            response = client.read_input_registers(address=address, count=1, unit=unit)
        else:
            return None, f"Nepodporovaná tabulka '{table}'."
    except ModbusException as exc:
        return None, str(exc)
    except Exception as exc:  # zachytí chyby socketu atd.
        return None, str(exc)

    if response.isError():
        return None, str(response)

    registers = getattr(response, "registers", None)
    if not registers:
        return None, "Prázdná odpověď z Modbusu."

    return int(registers[0]), None


def poll_register(
    client: ModbusTcpClient,
    connection: ConnectionConfig,
    reg_cfg: RegisterConfig,
) -> Dict[str, Any]:
    """Provede čtení jednoho registru včetně auto fallbacku."""

    ts = datetime.now(tz=timezone.utc).isoformat()
    address0 = register_to_address(reg_cfg.reg)
    ok = False
    table_used = reg_cfg.table
    raw_value: Optional[int] = None
    error_msg = ""

    if reg_cfg.table == "auto":
        # Nejprve se pokusíme o holding registr (podle zadání).
        holding_value, holding_error = read_single_table(
            client, "holding", address0, connection.unit
        )
        if holding_error is None and holding_value not in (None, 0):
            raw_value = holding_value
            table_used = "holding"
            ok = True
        else:
            input_value, input_error = read_single_table(
                client, "input", address0, connection.unit
            )
            if input_error is None and input_value not in (None, 0):
                raw_value = input_value
                table_used = "input"
                ok = True
            elif holding_error is None and holding_value is not None:
                raw_value = holding_value
                table_used = "holding"
                ok = True
                error_msg = input_error or ""
            elif input_error is None and input_value is not None:
                # holding selhal, ale vstupní registr alespoň něco vrátil.
                raw_value = input_value
                table_used = "input"
                ok = True
                error_msg = holding_error or ""
            else:
                error_msg = holding_error or input_error or "Neznámá chyba"
    else:
        raw_value, error_msg = read_single_table(
            client, reg_cfg.table, address0, connection.unit
        )
        ok = raw_value is not None and error_msg is None

    scaled_value: Optional[float] = None
    if raw_value is not None:
        scaled_value = raw_value * reg_cfg.scale

    return {
        "ts": ts,
        "name": reg_cfg.name,
        "reg": reg_cfg.reg,
        "address0": address0,
        "table": table_used,
        "raw": raw_value if raw_value is not None else "",
        "scaled": scaled_value if scaled_value is not None else "",
        "unit": reg_cfg.unit,
        "ok": ok,
        "error": error_msg or "",
    }


def run_once(
    client: ModbusTcpClient,
    connection: ConnectionConfig,
    registers: List[RegisterConfig],
    out_path: Path,
) -> None:
    """Provede jeden průchod přes všechny registrované položky."""

    delay = max(connection.delay_ms, 0) / 1000
    out_path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not out_path.exists() or out_path.stat().st_size == 0

    with out_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        if needs_header:
            writer.writeheader()

        for reg_cfg in registers:
            row = poll_register(client, connection, reg_cfg)
            writer.writerow(row)
            time.sleep(delay)


def parse_args() -> argparse.Namespace:
    """Zpracuje argumenty CLI."""

    parser = argparse.ArgumentParser(description="LG Therma V Modbus scanner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--once",
        action="store_true",
        help="Provede jednorázový průchod přes všechny registry.",
    )
    group.add_argument(
        "--interval",
        type=float,
        metavar="SECONDS",
        help="Opakuje průchod v daném intervalu (sekundy).",
    )
    parser.add_argument(
        "--yaml",
        default="registers.yaml",
        help="Cesta ke konfiguračnímu YAML souboru (default: registers.yaml).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Cesta k výstupnímu CSV souboru.",
    )
    return parser.parse_args()


def main() -> int:
    """Vstupní bod CLI."""

    args = parse_args()
    config_path = Path(args.yaml)
    out_path = Path(args.out)

    try:
        connection, registers = load_config(config_path)
    except (OSError, ValueError) as exc:
        print(f"Chybná konfigurace: {exc}", file=sys.stderr)
        return 1

    client = ModbusTcpClient(
        host=connection.host, port=connection.port, timeout=connection.timeout
    )

    if not client.connect():
        print(
            f"Nelze se připojit k {connection.host}:{connection.port} (unit={connection.unit}).",
            file=sys.stderr,
        )
        return 2

    try:
        if args.once:
            run_once(client, connection, registers, out_path)
        else:
            interval = max(args.interval, 0.1)
            while True:
                run_once(client, connection, registers, out_path)
                time.sleep(interval)
    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

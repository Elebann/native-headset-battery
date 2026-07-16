#!/usr/bin/env python3
import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

DEFAULT_INTERVAL = 30
CAPACITY_PATH = Path(
    "/sys/module/headset_battery_test/parameters/battery_capacity"
)
HEADSETCONTROL = "/usr/bin/headsetcontrol"


def read_headset_capacity() -> Optional[int]:
    """Obtiene el porcentaje reportado por HeadsetControl."""

    try:
        result = subprocess.run(
            [HEADSETCONTROL, "-b", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logging.error("HeadsetControl excedió el tiempo de espera")
        return None
    except OSError as error:
        logging.error("No se pudo ejecutar HeadsetControl: %s", error)
        return None

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        logging.warning("HeadsetControl falló: %s", message)
        return None

    try:
        payload = json.loads(result.stdout)
        devices = payload.get("devices", [])

        if not devices:
            logging.warning("HeadsetControl no devolvió dispositivos")
            return None

        device = devices[0]
        battery = device.get("battery", {})

        if (
            device.get("status") != "success"
            or battery.get("status") != "BATTERY_AVAILABLE"
        ):
            logging.warning("La batería no está disponible")
            return None

        capacity = int(battery["level"])

        if not 0 <= capacity <= 100:
            raise ValueError(f"porcentaje fuera de rango: {capacity}")

        return capacity

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        logging.error("Respuesta JSON inválida: %s", error)
        return None


def write_capacity(capacity: int) -> bool:
    """Actualiza el parámetro del módulo del kernel."""

    try:
        CAPACITY_PATH.write_text(f"{capacity}\n", encoding="utf-8")
        return True
    except PermissionError:
        logging.error(
            "Permiso denegado escribiendo en %s. "
            "Ejecuta el daemon como root.",
            CAPACITY_PATH,
        )
    except FileNotFoundError:
        logging.error(
            "No existe %s. ¿Está cargado headset_battery_test?",
            CAPACITY_PATH,
        )
    except OSError as error:
        logging.error("No se pudo actualizar la batería: %s", error)

    return False


def run(interval: int, once: bool) -> int:
    last_capacity: Optional[int] = None

    while True:
        capacity = read_headset_capacity()

        if capacity is not None and capacity != last_capacity:
            if write_capacity(capacity):
                logging.info("Batería actualizada: %d%%", capacity)
                last_capacity = capacity

        if once:
            return 0 if capacity is not None else 1

        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza HeadsetControl con power_supply"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Segundos entre consultas (predeterminado: 30)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Consulta y actualiza una sola vez",
    )
    args = parser.parse_args()

    if args.interval < 5:
        parser.error("El intervalo mínimo es de 5 segundos")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return run(args.interval, args.once)


if __name__ == "__main__":
    sys.exit(main())

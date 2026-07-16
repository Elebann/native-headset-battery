#!/usr/bin/env python3

import argparse
import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_INTERVAL = 30

MODULE_PARAMETERS = Path(
    "/sys/module/headset_battery_test/parameters"
)

CAPACITY_PATH = MODULE_PARAMETERS / "battery_capacity"
STATUS_PATH = MODULE_PARAMETERS / "battery_status"
ONLINE_PATH = MODULE_PARAMETERS / "battery_online"

HEADSETCONTROL = "/usr/bin/headsetcontrol"

STATUS_UNKNOWN = 0
STATUS_CHARGING = 1
STATUS_DISCHARGING = 2
STATUS_FULL = 4


@dataclass(frozen=True)
class BatteryState:
    capacity: Optional[int]
    status: int
    online: bool


def read_headset_state() -> BatteryState:
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
        return BatteryState(None, STATUS_UNKNOWN, False)
    except OSError as error:
        logging.error(
            "No se pudo ejecutar HeadsetControl: %s",
            error,
        )
        return BatteryState(None, STATUS_UNKNOWN, False)

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        logging.warning(
            "HeadsetControl falló: %s",
            message,
        )

        return BatteryState(None, STATUS_UNKNOWN, False)

    try:
        payload = json.loads(result.stdout)
        devices = payload.get("devices", [])

        if not devices:
            return BatteryState(None, STATUS_UNKNOWN, False)

        device = devices[0]

        if device.get("status") != "success":
            return BatteryState(None, STATUS_UNKNOWN, False)

        battery = device.get("battery", {})
        battery_status = battery.get("status")
        level = battery.get("level")

        if battery_status == "BATTERY_UNAVAILABLE":
            return BatteryState(
                capacity=None,
                status=STATUS_UNKNOWN,
                online=False,
            )

        if battery_status not in {
            "BATTERY_AVAILABLE",
            "BATTERY_CHARGING",
        }:
            logging.warning(
                "Estado de batería desconocido: %s",
                battery_status,
            )

            return BatteryState(None, STATUS_UNKNOWN, False)

        capacity = int(level)

        if not 0 <= capacity <= 100:
            raise ValueError(
                f"porcentaje fuera de rango: {capacity}"
            )

        if battery_status == "BATTERY_CHARGING":
            status = (
                STATUS_FULL
                if capacity >= 100
                else STATUS_CHARGING
            )
        else:
            status = STATUS_DISCHARGING

        return BatteryState(
            capacity=capacity,
            status=status,
            online=True,
        )

    except (
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        logging.error(
            "Respuesta JSON inválida: %s",
            error,
        )

        return BatteryState(None, STATUS_UNKNOWN, False)


def write_parameter(path: Path, value: int) -> bool:
    try:
        path.write_text(
            f"{value}\n",
            encoding="utf-8",
        )
        return True

    except PermissionError:
        logging.error(
            "Permiso denegado escribiendo en %s",
            path,
        )
    except FileNotFoundError:
        logging.error(
            "No existe %s. ¿Está cargado el módulo?",
            path,
        )
    except OSError as error:
        logging.error(
            "No se pudo escribir en %s: %s",
            path,
            error,
        )

    return False


def apply_state(
    current: BatteryState,
    previous: Optional[BatteryState],
) -> bool:
    success = True

    if previous is None or current.online != previous.online:
        success &= write_parameter(
            ONLINE_PATH,
            int(current.online),
        )

    if previous is None or current.status != previous.status:
        success &= write_parameter(
            STATUS_PATH,
            current.status,
        )

    if (
        current.capacity is not None
        and (
            previous is None
            or current.capacity != previous.capacity
        )
    ):
        success &= write_parameter(
            CAPACITY_PATH,
            current.capacity,
        )

    return success


def run(interval: int, once: bool) -> int:
    previous_state: Optional[BatteryState] = None

    while True:
        current_state = read_headset_state()

        if current_state != previous_state:
            if apply_state(current_state, previous_state):
                logging.info(
                    "Estado actualizado: online=%s, "
                    "status=%d, capacity=%s",
                    current_state.online,
                    current_state.status,
                    current_state.capacity,
                )

                previous_state = current_state

        if once:
            return 0

        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sincroniza HeadsetControl con power_supply"
        )
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help="Segundos entre consultas",
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Ejecuta una sola actualización",
    )

    args = parser.parse_args()

    if args.interval < 5:
        parser.error(
            "El intervalo mínimo es de 5 segundos"
        )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    return run(args.interval, args.once)


if __name__ == "__main__":
    sys.exit(main())

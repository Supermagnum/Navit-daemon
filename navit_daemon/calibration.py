"""
IMU calibration state: gyro bias, accel offset, and magnetometer bias.

Applied as: calibrated_gyro = raw_gyro - gyro_bias,
            calibrated_accel = raw_accel - accel_offset,
            calibrated_magnetometer = raw_magnetometer - magnetometer_bias.
Units: gyro_bias deg/s, accel_offset m/s^2, magnetometer_bias microtesla (uT).
"""

import json
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _to_triple(
    value: object, default: Tuple[float, float, float]
) -> Tuple[float, float, float]:
    """Convert list of 3 numbers to tuple; else return default."""
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        try:
            return (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            pass
    return default


class Calibration:
    """
    Mutable calibration: gyro bias, accel offset, and magnetometer bias.

    Bias/offset are subtracted from raw readings before fusion.
    """

    __slots__ = ("gyro_bias", "accel_offset", "magnetometer_bias")

    def __init__(
        self,
        gyro_bias: Optional[Tuple[float, float, float]] = None,
        accel_offset: Optional[Tuple[float, float, float]] = None,
        magnetometer_bias: Optional[Tuple[float, float, float]] = None,
    ) -> None:
        self.gyro_bias: Tuple[float, float, float] = gyro_bias or (0.0, 0.0, 0.0)
        self.accel_offset: Tuple[float, float, float] = accel_offset or (0.0, 0.0, 0.0)
        self.magnetometer_bias: Tuple[float, float, float] = magnetometer_bias or (
            0.0,
            0.0,
            0.0,
        )

    def apply_gyro(
        self, gyro: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Return gyro minus bias (deg/s)."""
        return (
            gyro[0] - self.gyro_bias[0],
            gyro[1] - self.gyro_bias[1],
            gyro[2] - self.gyro_bias[2],
        )

    def apply_accel(
        self, accel: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Return accel minus offset (m/s^2)."""
        return (
            accel[0] - self.accel_offset[0],
            accel[1] - self.accel_offset[1],
            accel[2] - self.accel_offset[2],
        )

    def apply_magnetometer(
        self, magnetometer: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """Return magnetometer minus bias (microtesla, uT)."""
        return (
            magnetometer[0] - self.magnetometer_bias[0],
            magnetometer[1] - self.magnetometer_bias[1],
            magnetometer[2] - self.magnetometer_bias[2],
        )

    def to_dict(self) -> dict:
        """Serialise to a JSON-suitable dict."""
        return {
            "gyro_bias": list(self.gyro_bias),
            "accel_offset": list(self.accel_offset),
            "magnetometer_bias": list(self.magnetometer_bias),
        }

    @classmethod
    def from_dict(cls, data: object) -> "Calibration":
        """Build from dict (e.g. JSON load). Unknown keys ignored."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            gyro_bias=_to_triple(data.get("gyro_bias"), (0.0, 0.0, 0.0)),
            accel_offset=_to_triple(data.get("accel_offset"), (0.0, 0.0, 0.0)),
            magnetometer_bias=_to_triple(
                data.get("magnetometer_bias"), (0.0, 0.0, 0.0)
            ),
        )


def load_calibration(path: Optional[Path]) -> Calibration:
    """Load calibration from a JSON file. Missing/invalid file returns default."""
    if not path or not path.exists():
        return Calibration()
    try:
        text = path.read_text()
        data = json.loads(text)
        return Calibration.from_dict(data)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Calibration load failed %s: %s", path, e)
        return Calibration()


def save_calibration(path: Path, calibration: Calibration) -> bool:
    """Write calibration to JSON file. Returns True on success."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(calibration.to_dict(), indent=2) + "\n")
        return True
    except OSError as e:
        logger.warning("Calibration save failed %s: %s", path, e)
        return False

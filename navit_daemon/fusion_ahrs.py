"""
AHRS fusion using imufusion: gyro + accelerometer -> orientation (yaw for heading).
"""

import logging
from typing import Any, Tuple

logger = logging.getLogger(__name__)

_Ahrs: Any = None
try:
    from imufusion import Ahrs

    _Ahrs = Ahrs
except ImportError:
    pass


class FusionAhrs:
    """
    Wrapper around imufusion Ahrs.

    Feed accelerometer (m/s^2) and gyroscope (deg/s) at each time step;
    get euler angles (roll, pitch, yaw in degrees). Yaw is used as heading.
    """

    def __init__(self, gain: float = 0.5) -> None:
        if _Ahrs is None:
            raise RuntimeError("imufusion not installed; pip install imufusion")
        self._ahrs = _Ahrs(gain=gain)
        self._yaw: float = 0.0
        self._pitch: float = 0.0
        self._roll: float = 0.0
        self._initialized = False

    def update(
        self,
        accel: Tuple[float, float, float],
        gyro: Tuple[float, float, float],
        sample_period_s: float,
    ) -> None:
        """
        Update AHRS with one IMU sample.

        accel: (x, y, z) in m/s^2
        gyro: (x, y, z) in deg/s
        sample_period_s: time since previous sample in seconds
        """
        self._ahrs.update(
            gyro,
            accel,
            sample_period_s,
        )
        euler = self._ahrs.quaternion.to_euler()
        self._roll, self._pitch, self._yaw = euler[0], euler[1], euler[2]
        self._initialized = True

    @property
    def yaw_deg(self) -> float:
        """Heading (yaw) in degrees [0, 360)."""
        y = self._yaw
        while y < 0:
            y += 360.0
        while y >= 360.0:
            y -= 360.0
        return y

    @property
    def pitch_deg(self) -> float:
        """Pitch in degrees."""
        return self._pitch

    @property
    def roll_deg(self) -> float:
        """Roll in degrees."""
        return self._roll

    @property
    def initialized(self) -> bool:
        """True after at least one update."""
        return self._initialized

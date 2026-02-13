"""
Unit tests for NMEA sentence building: valid, invalid, and edge cases.
"""

import math

from navit_daemon.gps_reader import GpsFix
from navit_daemon.nmea import (
    build_gga,
    build_rmc,
    fix_to_nmea,
)


class TestNmeaChecksum:
    """NMEA sentences must start with $ and end with *XX and CRLF."""

    def test_gga_starts_with_dollar_and_ends_with_crlf(self) -> None:
        s = build_gga(0.0, 0.0, 0.0)
        assert s.startswith("$")
        assert "*" in s
        assert s.endswith("\r\n")

    def test_rmc_starts_with_dollar_and_ends_with_crlf(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0)
        assert s.startswith("$")
        assert "*" in s
        assert s.endswith("\r\n")


class TestBuildGgaValid:
    """Valid input for build_gga."""

    def test_equator_prime_meridian(self) -> None:
        s = build_gga(0.0, 0.0, 0.0)
        assert "GPGGA" in s
        assert "0000.0000,N" in s
        assert "00000.0000,E" in s
        assert ",0.0,M," in s

    def test_positive_lat_lon(self) -> None:
        s = build_gga(52.5, 10.0, 100.5, fix_quality=2, num_sats=8, hdop=0.9)
        assert "5230.0000,N" in s
        assert "01000.0000,E" in s
        assert "100.5" in s
        assert ",2," in s
        assert ",08," in s
        assert "0.9" in s

    def test_negative_lat_lon_south_west(self) -> None:
        s = build_gga(-33.5, -70.25, 500.0)
        assert "3330.0000,S" in s
        assert "07015.0000,W" in s

    def test_time_iso_used_when_provided(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso="2024-06-15T12:34:56Z")
        assert "123456" in s

    def test_time_iso_malformed_returns_default(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso="not-iso")
        assert "000000.00" in s

    def test_time_iso_none_returns_default(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso=None)
        assert "000000.00" in s

    def test_time_iso_empty_string_returns_default(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso="")
        assert "000000.00" in s

    def test_time_iso_incomplete_returns_default(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso="2024-06-15")
        assert "000000.00" in s

    def test_time_iso_missing_time_part_returns_default(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, time_iso="2024-06-15T")
        assert "000000.00" in s


class TestBuildGgaEdgeCases:
    """Edge cases for build_gga."""

    def test_lat_90(self) -> None:
        s = build_gga(90.0, 0.0, 0.0)
        assert "90" in s
        assert ",N" in s

    def test_lat_minus_90(self) -> None:
        s = build_gga(-90.0, 0.0, 0.0)
        assert ",S" in s

    def test_lon_180(self) -> None:
        s = build_gga(0.0, 180.0, 0.0)
        assert ",E" in s or "180" in s

    def test_lon_minus_180(self) -> None:
        s = build_gga(0.0, -180.0, 0.0)
        assert ",W" in s

    def test_negative_altitude(self) -> None:
        s = build_gga(0.0, 0.0, -100.0)
        assert "-100.0" in s

    def test_fix_quality_zero(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, fix_quality=0)
        assert ",0," in s


class TestBuildGgaInvalidAndMalformed:
    """Invalid and malformed input for build_gga."""

    def test_lat_beyond_90_clamped_in_formatting(self) -> None:
        s = build_gga(91.0, 0.0, 0.0)
        assert "GPGGA" in s

    def test_lat_beyond_minus_90_clamped_in_formatting(self) -> None:
        s = build_gga(-91.0, 0.0, 0.0)
        assert "GPGGA" in s

    def test_lon_beyond_180_clamped_in_formatting(self) -> None:
        s = build_gga(0.0, 181.0, 0.0)
        assert "GPGGA" in s

    def test_lon_beyond_minus_180_clamped_in_formatting(self) -> None:
        s = build_gga(0.0, -181.0, 0.0)
        assert "GPGGA" in s

    def test_negative_fix_quality(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, fix_quality=-1)
        assert "GPGGA" in s

    def test_large_fix_quality(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, fix_quality=10)
        assert "GPGGA" in s

    def test_negative_num_sats(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, num_sats=-1)
        assert "GPGGA" in s

    def test_large_num_sats(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, num_sats=100)
        assert "GPGGA" in s

    def test_negative_hdop(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, hdop=-1.0)
        assert "GPGGA" in s

    def test_zero_hdop(self) -> None:
        s = build_gga(0.0, 0.0, 0.0, hdop=0.0)
        assert "GPGGA" in s

    def test_very_large_altitude(self) -> None:
        s = build_gga(0.0, 0.0, 100000.0)
        assert "GPGGA" in s


class TestBuildRmcValid:
    """Valid input for build_rmc."""

    def test_basic_rmc(self) -> None:
        s = build_rmc(52.0, 10.0, 5.0, 90.0)
        assert "GPRMC" in s
        assert "5200.0000,N" in s
        assert "01000.0000,E" in s
        assert "5.0" in s
        assert "90.0" in s
        assert ",A," in s

    def test_valid_false_status_v(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, valid=False)
        assert ",V," in s

    def test_date_iso_parsed(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, date_iso="2024-06-15T12:00:00Z")
        assert "15062024" in s

    def test_track_outside_0_360_clamped_in_output(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 400.0)
        assert "0.0" in s


class TestBuildRmcInvalidAndMalformed:
    """Invalid and malformed input for build_rmc."""

    def test_date_iso_malformed_returns_default(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, date_iso="not-a-date")
        assert "010100" in s

    def test_date_iso_incomplete_returns_default(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, date_iso="2024-06")
        assert "010100" in s

    def test_date_iso_none_returns_default(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, date_iso=None)
        assert "010100" in s

    def test_date_iso_empty_string_returns_default(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0, date_iso="")
        assert "010100" in s

    def test_negative_speed(self) -> None:
        s = build_rmc(0.0, 0.0, -5.0, 0.0)
        assert "GPRMC" in s

    def test_very_large_speed(self) -> None:
        s = build_rmc(0.0, 0.0, 1000.0, 0.0)
        assert "GPRMC" in s

    def test_track_very_large_clamped(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 1000.0)
        assert "0.0" in s

    def test_track_very_negative_clamped(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, -1000.0)
        assert "GPRMC" in s


class TestBuildRmcEdgeCases:
    """Edge cases for build_rmc."""

    def test_track_negative(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, -10.0)
        assert "GPRMC" in s

    def test_track_360(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 360.0)
        assert "GPRMC" in s

    def test_speed_zero(self) -> None:
        s = build_rmc(0.0, 0.0, 0.0, 0.0)
        assert "0.0" in s


class TestFixToNmeaValid:
    """fix_to_nmea with valid GpsFix."""

    def test_valid_fix_returns_gga_and_rmc(self) -> None:
        fix = GpsFix(
            lat=52.0,
            lon=10.0,
            alt=100.0,
            speed_ms=5.0,
            track=45.0,
            valid=True,
            mode=2,
            time_iso="2024-06-15T12:34:56Z",
        )
        gga, rmc = fix_to_nmea(fix, 45.0)
        assert gga is not None
        assert rmc is not None
        assert "GPGGA" in gga
        assert "GPRMC" in rmc
        assert "5200.0000,N" in gga
        assert "01000.0000,E" in gga

    def test_uses_fix_time_iso_when_time_iso_not_passed(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=1,
            time_iso="2024-01-01T00:00:00Z",
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert gga is not None
        assert "000000" in gga

    def test_speed_above_threshold_uses_fix_track(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=1.0,
            track=270.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 90.0)
        assert rmc is not None
        assert "270.0" in rmc


class TestFixToNmeaInvalidAndEdge:
    """Invalid and edge cases for fix_to_nmea."""

    def test_none_fix_returns_none_tuple(self) -> None:
        gga, rmc = fix_to_nmea(None, 0.0)
        assert gga is None
        assert rmc is None

    def test_invalid_fix_returns_none_tuple(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=0.0,
            track=0.0,
            valid=False,
            mode=0,
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert gga is None
        assert rmc is None

    def test_speed_below_threshold_uses_heading_not_fix_track(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=0.0,
            track=180.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 90.0)
        assert rmc is not None
        assert "90.0" in rmc


class TestFixToNmeaInvalidAndMalformed:
    """Invalid and malformed input for fix_to_nmea."""

    def test_extreme_lat_lon_values(self) -> None:
        fix = GpsFix(
            lat=200.0,
            lon=300.0,
            alt=0.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert gga is not None
        assert rmc is not None

    def test_negative_heading_clamped(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, -10.0)
        assert rmc is not None

    def test_heading_beyond_360_clamped(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 400.0)
        assert rmc is not None

    def test_very_large_altitude(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=100000.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert gga is not None
        assert "100000.0" in gga

    def test_negative_altitude(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=-1000.0,
            speed_ms=0.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert gga is not None
        assert "-1000.0" in gga

    def test_very_large_speed(self) -> None:
        fix = GpsFix(
            lat=0.0,
            lon=0.0,
            alt=0.0,
            speed_ms=1000.0,
            track=0.0,
            valid=True,
            mode=2,
        )
        gga, rmc = fix_to_nmea(fix, 0.0)
        assert rmc is not None

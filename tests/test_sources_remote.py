"""
Unit tests for remote source JSON parsing: valid, invalid, and edge cases.
"""

from navit_daemon.sources.remote import RemoteSource


class TestRemoteSourceParseLineValid:
    """Valid JSON input for remote protocol."""

    def test_imu_with_magnetometer(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line(
            '{"accel":[0.0,0.0,9.81],"gyro":[0.0,0.0,0.0],'
            '"magnetometer":[10.0,20.0,30.0]}'
        )
        sample = source.read()
        assert sample is not None
        accel, gyro, magnetometer = sample
        assert accel == (0.0, 0.0, 9.81)
        assert gyro == (0.0, 0.0, 0.0)
        assert magnetometer == (10.0, 20.0, 30.0)

    def test_imu_only_updates_read(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel":[0.0, 0.0, 9.81], "gyro":[0.0, 0.0, 0.0]}')
        sample = source.read()
        assert sample is not None
        accel, gyro, magnetometer = sample
        assert accel == (0.0, 0.0, 9.81)
        assert gyro == (0.0, 0.0, 0.0)
        assert magnetometer is None

    def test_gps_only_updates_get_fix(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line(
            '{"lat":52.5,"lon":10.1,"alt":100,"speed_ms":5.5,'
            '"track":90,"time_iso":"2024-06-15T12:00:00Z"}'
        )
        fix = source.get_fix()
        assert fix is not None
        assert fix.lat == 52.5
        assert fix.lon == 10.1
        assert fix.alt == 100.0
        assert fix.speed_ms == 5.5
        assert fix.track == 90.0
        assert fix.valid is True
        assert fix.time_iso == "2024-06-15T12:00:00Z"

    def test_combined_imu_and_gps(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line(
            '{"accel":[1,2,3],"gyro":[0.1,0.2,0.3],'
            '"lat":0,"lon":0,"alt":0,"speed_ms":0,"track":0}'
        )
        sample = source.read()
        assert sample == ((1.0, 2.0, 3.0), (0.1, 0.2, 0.3), None)
        fix = source.get_fix()
        assert fix is not None
        assert fix.lat == 0.0
        assert fix.lon == 0.0

    def test_gps_minimal_keys(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"lat":-45.0,"lon":170.0}')
        fix = source.get_fix()
        assert fix is not None
        assert fix.lat == -45.0
        assert fix.lon == 170.0
        assert fix.alt == 0.0
        assert fix.speed_ms == 0.0
        assert fix.track == 0.0
        assert fix.time_iso is None


class TestRemoteSourceParseLineInvalid:
    """Invalid input for remote protocol."""

    def test_empty_line_ignored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line("")
        assert source.read() is None
        assert source.get_fix() is None

    def test_invalid_json_ignored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel": [0, 0, 9.81]')  # missing closing brace
        assert source.read() is None

    def test_not_json_ignored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line("not json at all")
        assert source.read() is None
        assert source.get_fix() is None

    def test_imu_missing_gyro_not_stored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel":[0,0,9.81]}')
        assert source.read() is None

    def test_imu_short_list_ignored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel":[0,0],"gyro":[0,0,0]}')
        assert source.read() is None

    def test_gps_missing_lon_ignored(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"lat":52.0}')
        assert source.get_fix() is None


class TestRemoteSourceParseLineEdgeCases:
    """Edge cases for remote protocol."""

    def test_imu_numeric_strings_converted(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel":["0.1","0.2","9.81"],"gyro":["0","0","0"]}')
        sample = source.read()
        assert sample is not None
        accel, gyro, magnetometer = sample
        assert accel == (0.1, 0.2, 9.81)
        assert gyro == (0.0, 0.0, 0.0)
        assert magnetometer is None

    def test_time_iso_non_string_set_to_none(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"lat":0,"lon":0,"time_iso":123}')
        fix = source.get_fix()
        assert fix is not None
        assert fix.time_iso is None

    def test_read_before_any_parse_returns_none(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        assert source.read() is None
        assert source.get_fix() is None

    def test_latest_gps_overwrites_previous(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"lat":1,"lon":2}')
        source._parse_line('{"lat":3,"lon":4}')
        fix = source.get_fix()
        assert fix is not None
        assert fix.lat == 3.0
        assert fix.lon == 4.0

    def test_latest_imu_overwrites_previous(self) -> None:
        source = RemoteSource(host="127.0.0.1", port=0)
        source._parse_line('{"accel":[0,0,9.81],"gyro":[0,0,0]}')
        source._parse_line('{"accel":[1,1,10],"gyro":[1,1,1]}')
        sample = source.read()
        assert sample == ((1.0, 1.0, 10.0), (1.0, 1.0, 1.0), None)

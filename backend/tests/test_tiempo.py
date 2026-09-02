from datetime import datetime, timezone

from tiempo import a_bogota, ahora_bogota


def test_unix_utc_a_bogota_no_cambia_de_dia() -> None:
    # 1:15 UTC del 1 sep = 20:15 del 31 ago en Bogotá (UTC-5)
    utc = datetime(2026, 9, 1, 1, 15, tzinfo=timezone.utc)
    assert a_bogota(utc) == datetime(2026, 8, 31, 20, 15)
    assert a_bogota(int(utc.timestamp())) == datetime(2026, 8, 31, 20, 15)


def test_ahora_bogota_naive() -> None:
    ahora = ahora_bogota()
    assert ahora.tzinfo is None

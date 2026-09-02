from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db.models import Movimiento
from webhook.evolution import extraer_mensaje_entrada


def test_registra_gasto_por_texto(client: TestClient, seeded_session: Session) -> None:
    response = client.post(
        "/webhook/texto",
        json={
            "telefono": "573001112233",
            "texto": "gasté 15.300 en almuerzo",
            "enviado_en": "2026-08-31T20:15:00",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "registrado"
    assert body["mensaje"] == "✅ Registrado: $15.300 en Mercado"
    movimiento = seeded_session.query(Movimiento).one()
    assert movimiento.monto_cop == 15_300
    assert movimiento.fecha_registro == datetime(2026, 8, 31, 20, 15, 0)
    assert movimiento.fecha_gasto.isoformat() == "2026-08-31"


def test_numero_no_autorizado_se_ignora(client: TestClient, seeded_session: Session) -> None:
    response = client.post(
        "/webhook/texto",
        json={"telefono": "579998887766", "texto": "gasté 15.300 en almuerzo"},
    )
    assert response.json()["status"] == "ignored"
    assert seeded_session.query(Movimiento).count() == 0


def test_sin_monto_pide_aclaracion(client: TestClient, seeded_session: Session) -> None:
    response = client.post(
        "/webhook/texto",
        json={"telefono": "573001112233", "texto": "me gasté plata en uber"},
    )
    assert response.json()["status"] == "aclaracion"
    assert "monto" in response.json()["mensaje"].lower()
    assert seeded_session.query(Movimiento).count() == 0


def test_webhook_evolution_usa_hora_bogota_del_mensaje(
    client: TestClient, seeded_session: Session
) -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "15 mil en uber"},
            "messageTimestamp": int(datetime(2026, 9, 1, 1, 15, tzinfo=timezone.utc).timestamp()),
        },
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "registrado"
    movimiento = seeded_session.query(Movimiento).one()
    assert movimiento.monto_cop == 15_000
    assert movimiento.fecha_registro == datetime(2026, 8, 31, 20, 15)
    assert movimiento.fecha_gasto.isoformat() == "2026-08-31"


def test_evolution_ignora_grupos() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "120363@g.us"},
            "message": {"conversation": "gasté 10 mil"},
        },
    }
    assert extraer_mensaje_entrada(payload) is None


def test_evolution_ignora_salidas_a_otros_chats() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "573001112233@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {"conversation": "gasté 10 mil en uber"},
        },
    }
    assert extraer_mensaje_entrada(payload, numero_instancia="579998887766") is None


def test_evolution_acepta_chat_conmigo_mismo() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "573001112233@s.whatsapp.net",
                "fromMe": True,
            },
            "message": {"conversation": "gasté 10 mil en uber"},
        },
    }
    extraido = extraer_mensaje_entrada(payload, numero_instancia="573001112233")
    assert extraido is not None
    assert extraido.telefono == "573001112233"


def test_evolution_ignora_confirmacion_del_bot() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "✅ Registrado: $15.300 en Mercado"},
        },
    }
    assert extraer_mensaje_entrada(payload) is None


def test_evolution_lee_lid_con_sender_pn() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": "123456789012345@lid",
                "fromMe": False,
                "senderPn": "573001112233@s.whatsapp.net",
            },
            "message": {"conversation": "taxi 12000"},
        },
    }
    extraido = extraer_mensaje_entrada(payload)
    assert extraido is not None
    assert extraido.telefono == "573001112233"


def test_evolution_extended_text() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net"},
            "message": {"extendedTextMessage": {"text": "cine 28000"}},
        },
    }
    extraido = extraer_mensaje_entrada(payload)
    assert extraido is not None
    assert extraido.telefono == "573001112233"
    assert extraido.texto == "cine 28000"


def test_evolution_detecta_nota_de_voz_envuelta() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {
                "ephemeralMessage": {
                    "message": {
                        "audioMessage": {"ptt": True, "seconds": 4},
                    }
                }
            },
        },
    }
    extraido = extraer_mensaje_entrada(payload)
    assert extraido is not None
    assert extraido.es_audio is True


def test_evolution_detecta_nota_de_voz() -> None:
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {
                "audioMessage": {
                    "ptt": True,
                    "mimetype": "audio/ogg; codecs=opus",
                    "seconds": 4,
                }
            },
        },
    }
    extraido = extraer_mensaje_entrada(payload)
    assert extraido is not None
    assert extraido.es_audio is True
    assert extraido.texto == ""
    assert extraido.crudo is not None


def test_webhook_audio_registra_gasto(client: TestClient, seeded_session: Session, monkeypatch) -> None:
    from services.audio import ResultadoAudio

    monkeypatch.setattr(
        "main.transcribir_nota_voz",
        lambda _crudo: ResultadoAudio("gasté 15 mil en uber"),
    )
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {"audioMessage": {"ptt": True, "seconds": 3}},
        },
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "registrado"
    assert "15.000" in response.json()["mensaje"]
    movimiento = seeded_session.query(Movimiento).one()
    assert movimiento.monto_cop == 15_000
    assert movimiento.fue_audio is True


def test_webhook_audio_actualiza_gasto(client: TestClient, seeded_session: Session, monkeypatch) -> None:
    from services.audio import ResultadoAudio

    client.post(
        "/webhook/texto",
        json={"telefono": "573001112233", "texto": "uber 12000"},
    )
    monkeypatch.setattr(
        "main.transcribir_nota_voz",
        lambda _crudo: ResultadoAudio("actualiza uber a 15 mil"),
    )
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {"audioMessage": {"ptt": True, "seconds": 2}},
        },
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.json()["status"] == "comando"
    assert "15.000" in response.json()["mensaje"]
    assert seeded_session.query(Movimiento).one().monto_cop == 15_000


def test_webhook_audio_borra_ultimo(client: TestClient, seeded_session: Session, monkeypatch) -> None:
    from services.audio import ResultadoAudio

    client.post(
        "/webhook/texto",
        json={"telefono": "573001112233", "texto": "taxi 12000"},
    )
    monkeypatch.setattr(
        "main.transcribir_nota_voz",
        lambda _crudo: ResultadoAudio("borra el último"),
    )
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "573001112233@s.whatsapp.net", "fromMe": False},
            "message": {"audioMessage": {"ptt": True, "seconds": 2}},
        },
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.json()["status"] == "comando"
    assert "Borrado" in response.json()["mensaje"]
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.eliminado_en is not None


def test_webhook_audio_no_autorizado_no_transcribe(
    client: TestClient, seeded_session: Session, monkeypatch
) -> None:
    llamados: list[int] = []

    def _no(_crudo):
        llamados.append(1)
        raise AssertionError("no debe transcribir")

    monkeypatch.setattr("main.transcribir_nota_voz", _no)
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "579998887766@s.whatsapp.net", "fromMe": False},
            "message": {"audioMessage": {"ptt": True, "seconds": 2}},
        },
    }
    response = client.post("/webhook/evolution", json=payload)
    assert response.json()["status"] == "ignored"
    assert llamados == []


def test_texto_veinte_mil(client: TestClient, seeded_session: Session) -> None:
    response = client.post(
        "/webhook/texto",
        json={"telefono": "573001112233", "texto": "gasté veinte mil en uber"},
    )
    assert response.json()["status"] == "registrado"
    assert seeded_session.query(Movimiento).one().monto_cop == 20_000

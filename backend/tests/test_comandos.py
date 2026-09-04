from datetime import date, datetime

from sqlalchemy.orm import Session

from db.models import Movimiento
from services.comandos import interpretar_comando
from services.registro import procesar_mensaje


def test_interpreta_borrar_y_corregir() -> None:
    assert interpretar_comando("borra el último") is not None
    assert interpretar_comando("borra el último").accion == "borrar"
    cmd = interpretar_comando("corrige el último a 20.000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 20_000
    cmd = interpretar_comando("categoría del último: Transporte")
    assert cmd is not None
    assert cmd.accion == "cambiar_categoria"


def test_interpreta_sinonimos_y_texto_suelto() -> None:
    for frase in (
        "borra ultimo",
        "borra el último",
        "borra ultimo registro",
        "elimina ultimo registro",
        "suprime el último",
        "quita el ultimo gasto",
    ):
        cmd = interpretar_comando(frase)
        assert cmd is not None, frase
        assert cmd.accion == "borrar", frase
        assert cmd.consulta is None, frase

    cmd = interpretar_comando("borra gasto de maya")
    assert cmd is not None
    assert cmd.accion == "borrar"
    assert cmd.consulta == "maya"

    cmd = interpretar_comando("elimina el de maya")
    assert cmd is not None
    assert cmd.consulta == "maya"

    cmd = interpretar_comando("actualiza gasto de maya por 15000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 15_000
    assert cmd.consulta == "maya"

    cmd = interpretar_comando("cambia gasto de maya a 15.000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 15_000
    assert cmd.consulta == "maya"

    cmd = interpretar_comando("Modifica último otros a 190000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 190_000
    assert cmd.filtro_categoria == "Otros"

    cmd = interpretar_comando("actualiza el valor de pendajadas a 500000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 500_000
    assert cmd.consulta == "pendajadas"

    cmd = interpretar_comando("actualiza gasto de pendajadas po 5000000")
    assert cmd is not None
    assert cmd.accion == "corregir_monto"
    assert cmd.monto == 5_000_000
    assert cmd.consulta == "pendajadas"

    cmd = interpretar_comando("actualiza fecha de uber a ayer", hoy=date(2026, 9, 1))
    assert cmd is not None
    assert cmd.accion == "corregir_fecha"
    assert cmd.fecha_gasto == date(2026, 8, 31)
    assert cmd.consulta == "uber"

    cmd = interpretar_comando("cambia descripcion de uber a didi")
    assert cmd is not None
    assert cmd.accion == "corregir_descripcion"
    assert cmd.descripcion_nueva == "didi"
    assert cmd.consulta == "uber"

    cmd = interpretar_comando("cambia uber a didi")
    assert cmd is not None
    assert cmd.accion == "corregir_descripcion"
    assert cmd.descripcion_nueva == "didi"


def test_gasto_normal_no_es_comando() -> None:
    assert interpretar_comando("gasté 15.300 en almuerzo") is None
    assert interpretar_comando("Ingreso 20000") is None


def _msg(db: Session, texto: str, enviado_en: str | None = None):
    env = datetime.fromisoformat(enviado_en) if enviado_en else None
    return procesar_mensaje(db, telefono="573001112233", texto=texto, enviado_en=env)


def test_borra_ultimo(seeded_session: Session) -> None:
    _msg(seeded_session, "taxi 12000")
    assert seeded_session.query(Movimiento).count() == 1
    res = _msg(seeded_session, "borra el último")
    assert res.status == "comando"
    assert "Borrado" in res.mensaje_respuesta
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.eliminado_en is not None


def test_elimina_ultimo_registro(seeded_session: Session) -> None:
    _msg(seeded_session, "taxi 12000")
    res = _msg(seeded_session, "elimina ultimo registro")
    assert res.status == "comando"
    assert "Borrado" in res.mensaje_respuesta
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.eliminado_en is not None


def test_borra_por_descripcion(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 23300 en maya")
    _msg(seeded_session, "taxi 12000")
    res = _msg(seeded_session, "borra gasto de maya")
    assert res.status == "comando"
    assert "Borrado" not in res.mensaje_respuesta
    assert "¿Lo borro?" in res.mensaje_respuesta
    assert seeded_session.query(Movimiento).count() == 2
    maya = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 23_300).one()
    res = _msg(seeded_session, f"borra #{maya.id}")
    assert "Borrado" in res.mensaje_respuesta
    maya = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 23_300).one()
    seeded_session.refresh(maya)
    assert maya.eliminado_en is not None
    activos = seeded_session.query(Movimiento).filter(Movimiento.eliminado_en.is_(None)).all()
    assert len(activos) == 1
    assert activos[0].monto_cop == 12_000


def test_actualiza_por_descripcion(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 23300 en maya")
    res = _msg(seeded_session, "actualiza gasto de maya por 15000")
    assert res.status == "comando"
    assert "actualizado" in res.mensaje_respuesta.lower()
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.monto_cop == 15_000


def test_actualiza_valor_de_pendajadas(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 10000 en pendajadas")
    res = _msg(seeded_session, "actualiza el valor de pendajadas a 500000")
    assert res.status == "comando"
    assert "actualizado" in res.mensaje_respuesta.lower()
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.monto_cop == 500_000

    res = _msg(seeded_session, "actualiza gasto de pendajadas po 5000000")
    assert res.status == "comando"
    seeded_session.refresh(mov)
    assert mov.monto_cop == 5_000_000


def test_modifica_ultimo_otros_no_crea_gasto(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 50k en putas")
    _msg(seeded_session, "taxi 12000")
    res = _msg(seeded_session, "Modifica último otros a 190000")
    assert res.status == "comando"
    assert seeded_session.query(Movimiento).count() == 2
    actualizado = [m for m in seeded_session.query(Movimiento).all() if m.monto_cop == 190_000]
    taxi = [m for m in seeded_session.query(Movimiento).all() if m.monto_cop == 12_000]
    assert len(actualizado) == 1
    assert len(taxi) == 1


def test_corrige_ultimo(seeded_session: Session) -> None:
    _msg(seeded_session, "taxi 12000")
    res = _msg(seeded_session, "corrige el último a 15000")
    assert res.status == "comando"
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.monto_cop == 15000


def test_borra_por_id(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 23300 en maya")
    _msg(seeded_session, "taxi 12000")
    maya = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 23_300).one()
    res = _msg(seeded_session, f"borra #{maya.id}")
    assert res.status == "comando"
    seeded_session.refresh(maya)
    assert maya.eliminado_en is not None
    activos = seeded_session.query(Movimiento).filter(Movimiento.eliminado_en.is_(None)).all()
    assert len(activos) == 1
    assert activos[0].monto_cop == 12_000


def test_varios_maya_pide_aclarar(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 10000 en maya")
    _msg(seeded_session, "Gaste 20000 en maya")
    res = _msg(seeded_session, "borra gasto de maya")
    assert res.status == "comando"
    assert "Hay varios" in res.mensaje_respuesta
    assert "Cuál" in res.mensaje_respuesta or "cual" in res.mensaje_respuesta.lower()
    assert seeded_session.query(Movimiento).count() == 2


def test_dos_iguales_pregunta_con_hora(seeded_session: Session) -> None:
    _msg(seeded_session, "ayer gasté 20 mil en uber", "2026-08-31T20:27:12")
    _msg(seeded_session, "ayer gasté 20 mil en uber", "2026-08-31T20:27:31")
    res = _msg(seeded_session, "borra gasto de uber")
    assert res.status == "comando"
    assert "Hay varios (2) registros" in res.mensaje_respuesta
    assert "borrar" in res.mensaje_respuesta
    assert res.mensaje_respuesta.count("\n- ") >= 2
    assert "$20.000" in res.mensaje_respuesta
    assert "gasto" in res.mensaje_respuesta
    assert seeded_session.query(Movimiento).count() == 2

    res = _msg(seeded_session, "actualiza uber a 25000")
    assert "Hay varios (2) registros" in res.mensaje_respuesta
    assert "actualizar" in res.mensaje_respuesta
    assert seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 25_000).count() == 0


def test_actualiza_uber_con_pesos_pide_cual_si_hay_varios(seeded_session: Session) -> None:
    _msg(seeded_session, "ayer gasté 20 mil en uber")
    _msg(seeded_session, "gasté 15000 pesos en uber")
    res = _msg(seeded_session, "actualiza uber a 60 mil pesos")
    assert res.status == "comando"
    assert "Hay varios (2) registros" in res.mensaje_respuesta
    assert "actualizar" in res.mensaje_respuesta
    assert seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 60_000).count() == 0
    elegido = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 15_000).one()
    otro = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 20_000).one()
    res = _msg(seeded_session, str(elegido.id))
    assert "actualizado" in res.mensaje_respuesta.lower()
    seeded_session.refresh(elegido)
    seeded_session.refresh(otro)
    assert elegido.monto_cop == 60_000
    assert otro.monto_cop == 20_000


def test_elige_duplicado_con_solo_el_numero(seeded_session: Session) -> None:
    _msg(seeded_session, "ayer gasté 20 mil en uber")
    _msg(seeded_session, "ayer gasté 20 mil en uber")
    _msg(seeded_session, "elimina uber")
    ids = [m.id for m in seeded_session.query(Movimiento).order_by(Movimiento.id).all()]
    elegido = ids[0]
    res = _msg(seeded_session, str(elegido))
    assert res.status == "comando"
    assert "Borrado" in res.mensaje_respuesta
    borrado = seeded_session.query(Movimiento).filter(Movimiento.id == elegido).one()
    seeded_session.refresh(borrado)
    assert borrado.eliminado_en is not None
    activos = seeded_session.query(Movimiento).filter(Movimiento.eliminado_en.is_(None)).all()
    assert len(activos) == 1


def test_borra_el_id_sin_numeral(seeded_session: Session) -> None:
    _msg(seeded_session, "Gaste 23300 en maya")
    _msg(seeded_session, "taxi 12000")
    maya_id = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 23_300).first().id
    res = _msg(seeded_session, f"borra el {maya_id}")
    assert res.status == "comando"
    assert "Borrado" in res.mensaje_respuesta
    maya = seeded_session.get(Movimiento, maya_id)
    assert maya is not None and maya.eliminado_en is not None


def test_actualiza_fecha_del_ultimo(seeded_session: Session) -> None:
    _msg(seeded_session, "uber 12000", "2026-09-01T10:00:00")
    res = _msg(seeded_session, "actualiza la fecha del último a ayer", "2026-09-01T10:05:00")
    assert res.status == "comando"
    assert "Fecha actualizada" in res.mensaje_respuesta
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.fecha_gasto.isoformat() == "2026-08-31"


def test_actualiza_descripcion(seeded_session: Session) -> None:
    _msg(seeded_session, "uber 12000")
    res = _msg(seeded_session, "cambia descripción de uber a didi")
    assert res.status == "comando"
    assert "Descripción actualizada" in res.mensaje_respuesta
    mov = seeded_session.query(Movimiento).one()
    seeded_session.refresh(mov)
    assert mov.descripcion == "didi"


def test_actualiza_fecha_varios_pide_cual(seeded_session: Session) -> None:
    _msg(seeded_session, "uber 20000", "2026-09-01T10:00:00")
    _msg(seeded_session, "uber 15000", "2026-09-01T10:00:00")
    res = _msg(seeded_session, "actualiza fecha de uber a ayer", "2026-09-01T10:00:00")
    assert "Hay varios (2) registros" in res.mensaje_respuesta
    elegido = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 15_000).one()
    otro = seeded_session.query(Movimiento).filter(Movimiento.monto_cop == 20_000).one()
    res = _msg(seeded_session, str(elegido.id), "2026-09-01T10:01:00")
    assert "Fecha actualizada" in res.mensaje_respuesta
    seeded_session.refresh(elegido)
    seeded_session.refresh(otro)
    assert elegido.fecha_gasto.isoformat() == "2026-08-31"
    assert otro.fecha_gasto.isoformat() == "2026-09-01"

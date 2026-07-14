"""Script de emergencia para restablecer el PIN de un admin que lo olvidó.

*** MECANISMO DE EMERGENCIA TEMPORAL ***
Reemplazar por recuperación vía correo institucional cuando el login de
Microsoft Entra ID esté conectado. Mientras tanto, este script sobrescribe
directamente el PinAdmin de un usuario sin pedir el PIN actual — solo debe
ejecutarlo un desarrollador con acceso directo al servidor/base de datos,
nunca exponerlo como endpoint.

Uso: python -m scripts.resetear_pin_emergencia <usuario_id> <pin_nuevo>
"""

import re
import sys

from core.database import SessionLocal
from criterios.models import PinAdmin
from criterios.seguridad import hashear_pin
from usuarios.models import Usuario


def main() -> None:
    if len(sys.argv) != 3:
        print("Uso: python -m scripts.resetear_pin_emergencia <usuario_id> <pin_nuevo>")
        sys.exit(1)

    try:
        usuario_id = int(sys.argv[1])
    except ValueError:
        print(f"usuario_id inválido: '{sys.argv[1]}' debe ser un entero")
        sys.exit(1)

    pin_nuevo = sys.argv[2]
    if not re.fullmatch(r"\d{4,6}", pin_nuevo):
        print(f"pin_nuevo inválido: '{pin_nuevo}' debe ser numérico, de 4 a 6 dígitos")
        sys.exit(1)

    print("*** Este script es un mecanismo de emergencia TEMPORAL. ***")
    print("*** Reemplazar por recuperación vía correo cuando el login de Microsoft Entra ID esté conectado. ***\n")

    db = SessionLocal()
    try:
        usuario = db.get(Usuario, usuario_id)
        if not usuario:
            print(f"No existe un usuario con id={usuario_id}")
            sys.exit(1)
        if usuario.rol.value != "admin":
            print(f"Advertencia: el usuario {usuario_id} ({usuario.nombre}) no tiene rol admin actualmente.")

        nombre, correo = usuario.nombre, usuario.correo

        pin_existente = db.query(PinAdmin).filter_by(usuario_id=usuario_id).first()
        if pin_existente:
            pin_existente.pin_hash = hashear_pin(pin_nuevo)
            accion = "actualizado"
        else:
            db.add(PinAdmin(usuario_id=usuario_id, pin_hash=hashear_pin(pin_nuevo)))
            accion = "creado"
        db.commit()
    finally:
        db.close()

    print(f"PIN {accion} para el usuario {usuario_id} ({nombre}, {correo}).")


if __name__ == "__main__":
    main()

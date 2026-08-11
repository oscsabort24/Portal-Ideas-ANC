"""Cálculo de la calificación y prioridad RICE, según la matriz de la
política de ANC. SIEMPRE se recalcula en el backend a partir de los
campos de entrada — comites/router.py nunca confía en un valor de
calificacion/prioridad que venga del cliente (ver comites/models.py:RiceEvaluacion).
"""

from comites.models import NivelEsfuerzo, NivelImpactoConfianza, PresupuestoRango, PrioridadRice

_VALOR_IMPACTO_CONFIANZA = {
    NivelImpactoConfianza.muy_bajo: 0.25,
    NivelImpactoConfianza.medio: 0.5,
    NivelImpactoConfianza.alto: 0.75,
    NivelImpactoConfianza.muy_alto: 1.0,
}

_VALOR_ESFUERZO = {
    NivelEsfuerzo.corto_plazo: 3,
    NivelEsfuerzo.medio_plazo: 2,
    NivelEsfuerzo.largo_plazo: 1,
}

_VALOR_PRESUPUESTO = {
    PresupuestoRango.cero: 0.10,
    PresupuestoRango.hasta_10000: 0.25,
    PresupuestoRango.hasta_20000: 0.50,
    PresupuestoRango.hasta_30000: 0.75,
    PresupuestoRango.mas_30000: 1.00,
}


def calcular_calificacion(
    alcance_departamentos: int,
    impacto: NivelImpactoConfianza,
    confianza: NivelImpactoConfianza,
    esfuerzo: NivelEsfuerzo,
    paises: int,
    presupuesto_rango: PresupuestoRango,
    impacta_plan_estrategico: bool = False,
) -> tuple[float, PrioridadRice]:
    calificacion = (
        (alcance_departamentos * _VALOR_IMPACTO_CONFIANZA[impacto] * _VALOR_IMPACTO_CONFIANZA[confianza])
        / (_VALOR_ESFUERZO[esfuerzo] + paises)
    ) * _VALOR_PRESUPUESTO[presupuesto_rango]

    # OVERRIDE DE NEGOCIO (no está en el texto literal de la política
    # ANCCR8.1P143-0 — esa política solo captura impacta_plan_estrategico
    # como un dato Sí/No de la matriz, sin conectarlo a la fórmula de
    # priorización). Decisión explícita de Oscar Saborío (Business Analyst):
    # si la idea impacta el plan estratégico, la Prioridad SIEMPRE es alta,
    # sin importar qué tan baja salga la Calificación numérica. Se deja
    # documentado acá para que quede trazable si alguien pregunta después
    # por qué el sistema se comporta así.
    if impacta_plan_estrategico:
        return calificacion, PrioridadRice.alta

    if calificacion <= 3.3:
        prioridad = PrioridadRice.baja
    elif calificacion <= 6.6:
        prioridad = PrioridadRice.media
    else:
        prioridad = PrioridadRice.alta

    return calificacion, prioridad

/**
 * Reglas del motivo de rechazo, compartidas por los DOS puntos donde una idea
 * puede rechazarse: revisión de área (MisRevisiones) y comité (ColaComite).
 *
 * Espejo de v1.0/core/rechazo.py — el backend es la autoridad y devuelve 400
 * si no se cumple; esto existe para que la persona lo sepa MIENTRAS escribe,
 * en vez de enterarse al apretar el botón.
 */

/** Debe coincidir con MIN_MOTIVO_RECHAZO en v1.0/core/rechazo.py. */
export const MIN_MOTIVO_RECHAZO = 20

/** Cuenta sobre el texto recortado: 20 espacios no son un motivo. */
export function motivoValido(texto: string): boolean {
  return texto.trim().length >= MIN_MOTIVO_RECHAZO
}

/** Mensaje bajo el campo, o null si ya cumple. */
export function ayudaMotivo(texto: string): string | null {
  const faltan = MIN_MOTIVO_RECHAZO - texto.trim().length
  if (faltan <= 0) return null
  if (texto.trim().length === 0) {
    return `Explicá por qué se rechaza — mínimo ${MIN_MOTIVO_RECHAZO} caracteres. Es la única explicación que recibe quien propuso la idea.`
  }
  return `Sé un poco más específico: faltan ${faltan} caractere${faltan === 1 ? '' : 's'}.`
}

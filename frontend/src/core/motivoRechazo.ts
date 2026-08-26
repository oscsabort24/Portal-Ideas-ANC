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

/** Mensaje bajo el campo, o null si ya cumple.
 *
 * El texto del campo vacío es común a rechazar y a pedir cambios: los dos
 * son explicaciones que recibe el autor y comparten el mismo mínimo, así que
 * no dice "por qué se rechaza" — serviría solo para uno de los dos. */
export function ayudaMotivo(texto: string): string | null {
  const largo = texto.trim().length
  const faltan = MIN_MOTIVO_RECHAZO - largo
  if (faltan <= 0) return null
  if (largo === 0) {
    return `Explicá con detalle — mínimo ${MIN_MOTIVO_RECHAZO} caracteres. Es lo único que recibe quien propuso la idea.`
  }
  return `Sé un poco más específico: faltan ${faltan} caractere${faltan === 1 ? '' : 's'}.`
}

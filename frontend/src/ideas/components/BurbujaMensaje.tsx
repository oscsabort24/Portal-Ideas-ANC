import type { MensajeEntrevista } from '../types'

/**
 * Una burbuja del chat de la entrevista.
 *
 * Tres roles, no dos: además del autor y la IA, un revisor de área puede
 * dejar un comentario al pedir cambios. Antes esos se guardaban como
 * 'asistente' y el autor los leía como si fueran de la IA — por eso acá el
 * rol de revisor tiene nombre visible y estilo propio, distinto de los otros
 * dos.
 */
export default function BurbujaMensaje({ mensaje }: { mensaje: MensajeEntrevista }) {
  if (mensaje.rol === 'revisor') {
    return (
      <div className="message revisor">
        <div className="msg-autor-revisor">
          {mensaje.usuario?.nombre ?? 'El revisor de área'} pidió cambios:
        </div>
        <div className="msg-bubble msg-bubble-revisor">{mensaje.contenido}</div>
      </div>
    )
  }

  const esUsuario = mensaje.rol === 'usuario'
  return (
    <div className={`message ${esUsuario ? 'user' : 'assistant'}`}>
      <div className="msg-bubble">{mensaje.contenido}</div>
    </div>
  )
}

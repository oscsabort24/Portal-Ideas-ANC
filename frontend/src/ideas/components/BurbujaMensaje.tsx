import type { MensajeEntrevista } from '../types'

export default function BurbujaMensaje({ mensaje }: { mensaje: MensajeEntrevista }) {
  const esUsuario = mensaje.rol === 'usuario'
  return (
    <div className={`message ${esUsuario ? 'user' : 'assistant'}`}>
      <div className="msg-bubble">{mensaje.contenido}</div>
    </div>
  )
}

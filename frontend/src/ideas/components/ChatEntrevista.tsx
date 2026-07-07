import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useParams } from 'react-router-dom'
import { enviarMensaje, obtenerIdea } from '../api'
import type { IdeaDetalle, MensajeEntrevista } from '../types'
import BurbujaMensaje from './BurbujaMensaje'

export default function ChatEntrevista() {
  const { id } = useParams<{ id: string }>()
  const ideaId = Number(id)

  const [idea, setIdea] = useState<IdeaDetalle | null>(null)
  const [mensajes, setMensajes] = useState<MensajeEntrevista[]>([])
  const [contenido, setContenido] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(true)
  const finMensajesRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    obtenerIdea(ideaId)
      .then((detalle) => {
        if (cancelado) return
        setIdea(detalle)
        setMensajes(detalle.mensajes)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la idea'))
      .finally(() => setCargando(false))
    return () => {
      cancelado = true
    }
  }, [ideaId])

  useEffect(() => {
    finMensajesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes])

  async function handleEnviar() {
    const texto = contenido.trim()
    if (!texto || enviando || idea?.estado === 'enviada') return

    setEnviando(true)
    setError(null)
    try {
      const respuesta = await enviarMensaje(ideaId, texto)
      setMensajes((prev) => [...prev, respuesta.mensaje_usuario, respuesta.mensaje_asistente])
      setIdea((prev) => (prev ? { ...prev, estado: respuesta.idea.estado, fecha_envio: respuesta.idea.fecha_envio } : prev))
      setContenido('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar el mensaje')
    } finally {
      setEnviando(false)
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEnviar()
    }
  }

  if (cargando) return <p>Cargando...</p>
  if (!idea) return <p style={{ color: 'var(--error)' }}>{error ?? 'Idea no encontrada'}</p>

  const entrevistaTerminada = idea.estado === 'enviada'

  return (
    <div className="chat-shell">
      <div className="chat-titulo">{idea.titulo}</div>

      <div className="messages-container">
        {mensajes.map((m) => (
          <BurbujaMensaje key={m.id} mensaje={m} />
        ))}
        <div ref={finMensajesRef} />
      </div>

      {entrevistaTerminada && (
        <div className="banner-enviada">✓ Idea enviada — la entrevista quedó registrada.</div>
      )}

      {error && <p style={{ color: 'var(--error)', fontSize: 13, padding: '0 20px' }}>{error}</p>}

      <div className="input-area">
        <div className={`input-wrapper ${entrevistaTerminada ? 'disabled' : ''}`}>
          <textarea
            id="userInput"
            rows={1}
            placeholder={entrevistaTerminada ? 'Esta idea ya fue enviada' : 'Escribe tu respuesta...'}
            value={contenido}
            onChange={(e) => setContenido(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={entrevistaTerminada || enviando}
          />
          <button
            className="btn-send"
            onClick={handleEnviar}
            disabled={entrevistaTerminada || enviando || !contenido.trim()}
            aria-label="Enviar mensaje"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}

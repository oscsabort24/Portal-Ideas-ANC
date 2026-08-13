import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { FiMessageCircle } from 'react-icons/fi'
import { obtenerIdea, obtenerResumen, preguntarSobreIdea } from '../api'
import type { MensajeEntrevista } from '../types'

interface PreguntaRespuesta {
  pregunta: string
  respuesta: string
}

const ETIQUETA_CATEGORIA_RIESGO: Record<string, string> = {
  bajo: 'Bajo',
  moderado: 'Moderado',
  medio_alto: 'Medio-Alto',
  alto: 'Alto',
  critico: 'Crítico',
}

const COLOR_CATEGORIA_RIESGO: Record<string, { bg: string; color: string }> = {
  bajo: { bg: 'var(--success-bg)', color: 'var(--success)' },
  moderado: { bg: 'var(--primary-faint)', color: 'var(--primary)' },
  medio_alto: { bg: 'var(--partial-bg)', color: 'var(--partial)' },
  alto: { bg: 'var(--partial-bg)', color: 'var(--partial)' },
  critico: { bg: 'var(--error-bg)', color: 'var(--error)' },
}

export default function ResumenYPreguntas({
  ideaId,
  origen,
}: {
  ideaId: number
  origen: 'revision' | 'comite'
}) {
  const [resumen, setResumen] = useState<string | null>(null)
  const [categoriaRiesgo, setCategoriaRiesgo] = useState<string | null>(null)
  const [resumenNoDisponible, setResumenNoDisponible] = useState<string | null>(null)
  const [cargandoResumen, setCargandoResumen] = useState(true)
  const [historial, setHistorial] = useState<PreguntaRespuesta[]>([])
  const [preguntaActual, setPreguntaActual] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [transcriptAbierto, setTranscriptAbierto] = useState(false)
  const [transcriptMensajes, setTranscriptMensajes] = useState<MensajeEntrevista[] | null>(null)
  const [cargandoTranscript, setCargandoTranscript] = useState(false)
  const [errorTranscript, setErrorTranscript] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setCargandoResumen(true)
    setResumen(null)
    setCategoriaRiesgo(null)
    setResumenNoDisponible(null)
    setHistorial([])
    obtenerResumen(ideaId)
      .then(({ resumen: texto, categoria_riesgo }) => {
        if (!cancelado) {
          setResumen(texto)
          setCategoriaRiesgo(categoria_riesgo)
        }
      })
      .catch((err) => {
        // Una idea sin ningún mensaje de la IA todavía (caso raro) no es un
        // error real que mostrar en rojo — solo no hay resumen que ofrecer.
        if (!cancelado) setResumenNoDisponible(err instanceof Error ? err.message : 'No hay resumen disponible')
      })
      .finally(() => {
        if (!cancelado) setCargandoResumen(false)
      })
    return () => {
      cancelado = true
    }
  }, [ideaId])

  async function handlePreguntar() {
    const pregunta = preguntaActual.trim()
    if (!pregunta) return
    setEnviando(true)
    setError(null)
    try {
      const { respuesta } = await preguntarSobreIdea(ideaId, pregunta, origen)
      setHistorial((prev) => [...prev, { pregunta, respuesta }])
      setPreguntaActual('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo procesar la pregunta')
    } finally {
      setEnviando(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !enviando) {
      e.preventDefault()
      handlePreguntar()
    }
  }

  function handleVerEntrevistaCompleta() {
    setTranscriptAbierto(true)
    if (transcriptMensajes !== null) return
    setCargandoTranscript(true)
    setErrorTranscript(null)
    obtenerIdea(ideaId)
      .then((idea) => setTranscriptMensajes(idea.mensajes))
      .catch((err) => setErrorTranscript(err instanceof Error ? err.message : 'No se pudo cargar la entrevista'))
      .finally(() => setCargandoTranscript(false))
  }

  return (
    <div className="form-card" style={{ marginBottom: 16 }}>
      <p className="form-label">
        Resumen de la idea
        {categoriaRiesgo && (
          <span
            style={{
              marginLeft: 8,
              fontSize: 11.5,
              fontWeight: 700,
              padding: '3px 10px',
              borderRadius: 20,
              textTransform: 'none',
              letterSpacing: 'normal',
              background: (COLOR_CATEGORIA_RIESGO[categoriaRiesgo] ?? COLOR_CATEGORIA_RIESGO.moderado).bg,
              color: (COLOR_CATEGORIA_RIESGO[categoriaRiesgo] ?? COLOR_CATEGORIA_RIESGO.moderado).color,
            }}
          >
            Riesgo: {ETIQUETA_CATEGORIA_RIESGO[categoriaRiesgo] ?? categoriaRiesgo}
          </span>
        )}
      </p>

      {cargandoResumen && <p style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>Cargando resumen...</p>}

      {!cargandoResumen && resumen && (
        <div
          style={{
            background: 'var(--primary-faint)',
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius)',
            padding: '12px 14px',
            fontSize: 13.5,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
          }}
        >
          {resumen}
        </div>
      )}

      {!cargandoResumen && resumenNoDisponible && (
        <p style={{ color: 'var(--text-muted)', fontSize: 13, fontStyle: 'italic' }}>{resumenNoDisponible}</p>
      )}

      {origen === 'revision' && (
        <button className="btn-small" style={{ marginTop: 4 }} onClick={handleVerEntrevistaCompleta}>
          Ver entrevista completa
        </button>
      )}

      <p className="form-label" style={{ marginTop: 16 }}>
        <FiMessageCircle style={{ marginRight: 4, verticalAlign: 'middle' }} />
        Preguntas sobre esta idea
      </p>

      {historial.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 10 }}>
          {historial.map((item, i) => (
            <div key={i}>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text)' }}>{item.pregunta}</div>
              <div
                style={{
                  fontSize: 13.5,
                  color: 'var(--text-muted)',
                  marginTop: 2,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {item.respuesta}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="form-error">{error}</p>}

      <div className="form-row">
        <input
          type="text"
          className="form-input"
          placeholder="Escribe una pregunta sobre esta idea..."
          value={preguntaActual}
          onChange={(e) => setPreguntaActual(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={enviando}
        />
        <button className="btn-secundario" disabled={enviando || !preguntaActual.trim()} onClick={handlePreguntar}>
          {enviando ? 'Preguntando...' : 'Preguntar'}
        </button>
      </div>

      {transcriptAbierto &&
        createPortal(
          // Portal a document.body: este modal se abre desde dentro de una
          // idea-card en una lista (MisRevisiones.tsx) — quedándose anidado
          // en ese árbol, cualquier ancestro que genere un containing block
          // (transform en hover, contenedor con scroll propio, etc.) puede
          // atrapar el position:fixed y hacer que el overlay solo cubra esa
          // card en vez de la pantalla completa, mezclándose visualmente con
          // el resto del contenido. El portal lo saca de ese árbol de DOM
          // por completo (los eventos de React siguen burbujeando normal).
          <div
            className="preview-overlay"
            onClick={(e) => e.target === e.currentTarget && setTranscriptAbierto(false)}
            role="dialog"
            aria-modal="true"
          >
            <div className="preview-modal">
              <div className="preview-modal-header">
                <span className="preview-modal-title">Entrevista completa</span>
                <button
                  className="preview-modal-close"
                  onClick={() => setTranscriptAbierto(false)}
                  aria-label="Cerrar entrevista completa"
                >
                  ×
                </button>
              </div>
              <div
                className="preview-modal-body"
                style={{ padding: '16px 20px', overflowY: 'auto', maxHeight: '70vh' }}
              >
                {cargandoTranscript && <p style={{ color: 'var(--text-muted)' }}>Cargando entrevista...</p>}
                {errorTranscript && <p className="form-error">{errorTranscript}</p>}
                {!cargandoTranscript && !errorTranscript && transcriptMensajes && transcriptMensajes.length === 0 && (
                  <p style={{ color: 'var(--text-muted)' }}>Esta idea todavía no tiene mensajes en su entrevista.</p>
                )}
                {!cargandoTranscript && transcriptMensajes && transcriptMensajes.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {transcriptMensajes.map((m) => (
                      <div key={m.id} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>
                          {m.rol === 'usuario' ? 'Colaborador' : 'Asistente IA'}
                        </span>
                        <span style={{ fontSize: 13.5, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{m.contenido}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </div>
  )
}

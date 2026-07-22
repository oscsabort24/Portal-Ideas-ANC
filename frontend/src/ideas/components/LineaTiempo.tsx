import { useEffect, useState } from 'react'
import { obtenerLineaTiempo } from '../api'
import type { ColorEvento, EventoLineaTiempo } from '../types'

const COLOR_VAR: Record<ColorEvento, string> = {
  exito: 'var(--success)',
  advertencia: 'var(--partial)',
  peligro: 'var(--error)',
  info: 'var(--primary)',
}

function formatearFecha(iso: string): string {
  return new Date(iso).toLocaleString('es-CR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function LineaTiempo({ ideaId }: { ideaId: number }) {
  const [eventos, setEventos] = useState<EventoLineaTiempo[] | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    setError(null)
    obtenerLineaTiempo(ideaId)
      .then((data) => {
        if (!cancelado) setEventos(data)
      })
      .catch((err) => {
        // No se traga el error: se guarda aparte (y se loguea) para
        // mostrarlo explícito en vez de dejar el componente en blanco.
        console.error('No se pudo cargar la línea de tiempo:', err)
        if (!cancelado) setError(err instanceof Error ? err.message : 'Error desconocido')
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [ideaId])

  // Única excepción a "siempre mostrar el encabezado": mientras carga la
  // primera vez, solo el indicador de carga — evita un parpadeo de "Sin
  // eventos todavía" un instante antes de que lleguen los datos reales.
  if (cargando) {
    return (
      <div style={{ padding: '20px', borderTop: '1px solid var(--border-light)' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>Cargando historial...</p>
      </div>
    )
  }

  // El backend devuelve orden cronológico ascendente — se invierte para
  // mostrar el evento más reciente arriba.
  const eventosOrdenados = eventos ? [...eventos].reverse() : []

  return (
    <div style={{ padding: '20px', borderTop: '1px solid var(--border-light)' }}>
      <h2 className="page-title" style={{ fontSize: 18, marginBottom: 12 }}>
        Historial de la idea
      </h2>

      {error && <p style={{ color: 'var(--error)', fontSize: 13.5 }}>No se pudo cargar el historial de la idea</p>}

      {!error && eventos && eventos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>Sin eventos todavía.</p>
      )}

      {!error && eventos && eventos.length > 0 && (
        <div className="linea-tiempo">
          {eventosOrdenados.map((evento, i) => (
            <div key={i} className="linea-tiempo-item">
              <span className="linea-tiempo-punto" style={{ background: COLOR_VAR[evento.color] }} />
              <div className="linea-tiempo-contenido">
                <div className="linea-tiempo-descripcion">{evento.descripcion}</div>
                <div className="linea-tiempo-fecha">{formatearFecha(evento.fecha)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

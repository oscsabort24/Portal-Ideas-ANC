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
  const [eventos, setEventos] = useState<EventoLineaTiempo[]>([])
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let cancelado = false
    obtenerLineaTiempo(ideaId)
      .then((data) => {
        if (!cancelado) setEventos(data)
      })
      .catch(() => {
        if (!cancelado) setEventos([])
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [ideaId])

  if (cargando || eventos.length === 0) return null

  // El backend devuelve orden cronológico ascendente — se invierte para
  // mostrar el evento más reciente arriba.
  const eventosOrdenados = [...eventos].reverse()

  return (
    <div style={{ padding: '20px', borderTop: '1px solid var(--border-light)' }}>
      <h2 className="page-title" style={{ fontSize: 18, marginBottom: 12 }}>
        Historial de la idea
      </h2>

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
    </div>
  )
}

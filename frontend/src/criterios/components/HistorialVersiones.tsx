import { FiClock } from 'react-icons/fi'
import type { CriterioIA } from '../types'

export default function HistorialVersiones({ historial }: { historial: CriterioIA[] }) {
  const anteriores = historial.filter((c) => !c.activo)

  if (anteriores.length === 0) {
    return <p className="cab-vacio">Todavía no hay versiones anteriores.</p>
  }

  return (
    <div className="lista-simple">
      {anteriores.map((c) => {
        const fecha = new Date(c.creado_en).toLocaleString('es-CR', {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
        const extracto = c.contenido.length > 80 ? `${c.contenido.slice(0, 80)}…` : c.contenido
        return (
          <div key={c.id} className="item-simple">
            <FiClock className="item-simple-icon" />
            <span>Versión {c.version} — {extracto}</span>
            <span className="item-simple-secundario">{c.creado_por.nombre} · {fecha}</span>
          </div>
        )
      })}
    </div>
  )
}

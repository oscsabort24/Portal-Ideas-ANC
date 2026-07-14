import { FiClock } from 'react-icons/fi'
import type { DocumentoCriterio } from '../types'

export default function HistorialVersiones({ historial }: { historial: DocumentoCriterio[] }) {
  const anteriores = historial.filter((d) => !d.activo)

  if (anteriores.length === 0) {
    return <p className="cab-vacio">Todavía no hay versiones anteriores.</p>
  }

  return (
    <div className="lista-simple">
      {anteriores.map((d) => {
        const fecha = new Date(d.subido_en).toLocaleString('es-CR', {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
        return (
          <div key={d.id} className="item-simple">
            <FiClock className="item-simple-icon" />
            <span>Versión {d.version} — {d.nombre_archivo}</span>
            <span className="item-simple-secundario">{d.subido_por.nombre} · {fecha}</span>
          </div>
        )
      })}
    </div>
  )
}

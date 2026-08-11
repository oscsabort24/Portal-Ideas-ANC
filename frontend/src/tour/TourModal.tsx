import { useEffect, useState } from 'react'
import { FiX } from 'react-icons/fi'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import { pasosVisiblesParaRol } from './pasos'

export default function TourModal({ onCerrar }: { onCerrar: () => void }) {
  const usuarioActual = useUsuarioActual()
  const pasos = pasosVisiblesParaRol(usuarioActual.rol)
  const [paso, setPaso] = useState(0)

  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onCerrar])

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCerrar()
  }

  const esUltimo = paso === pasos.length - 1
  const actual = pasos[paso]

  return (
    <div className="tour-overlay" onClick={handleOverlayClick} role="dialog" aria-modal="true">
      <div className="tour-modal">
        <div className="tour-modal-header">
          <span className="tour-modal-title">{actual.titulo}</span>
          <button className="tour-modal-close" onClick={onCerrar} aria-label="Cerrar tour">
            <FiX />
          </button>
        </div>

        <div className="tour-modal-body">
          <p>{actual.texto}</p>
        </div>

        <div className="tour-modal-footer">
          <div className="tour-modal-puntos">
            {pasos.map((_, i) => (
              <span key={i} className={`tour-modal-punto ${i === paso ? 'activo' : ''}`} />
            ))}
          </div>

          <div className="tour-modal-acciones">
            {!esUltimo && (
              <button className="btn-secundario" onClick={onCerrar}>
                Saltar
              </button>
            )}
            {paso > 0 && (
              <button className="btn-secundario" onClick={() => setPaso((p) => p - 1)}>
                Anterior
              </button>
            )}
            {esUltimo ? (
              <button className="btn-primary" onClick={onCerrar}>
                Entendido
              </button>
            ) : (
              <button className="btn-primary" onClick={() => setPaso((p) => p + 1)}>
                Siguiente
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

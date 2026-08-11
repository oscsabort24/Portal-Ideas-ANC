import { useEffect, useState } from 'react'
import { FiHelpCircle, FiX } from 'react-icons/fi'
import { useLocation } from 'react-router-dom'
import { obtenerAyudaPagina } from './ayudaPorPagina'

export default function AyudaContextual() {
  const location = useLocation()
  const [abierto, setAbierto] = useState(false)
  const ayuda = obtenerAyudaPagina(location.pathname)

  // Evita que la ayuda de la pantalla anterior quede abierta al navegar.
  useEffect(() => {
    setAbierto(false)
  }, [location.pathname])

  if (!ayuda) return null

  return (
    <>
      <button
        className="ayuda-contextual-boton"
        onClick={() => setAbierto((prev) => !prev)}
        title="Ayuda de esta pantalla"
        aria-label="Ayuda de esta pantalla"
      >
        <FiHelpCircle />
      </button>

      {abierto && (
        <div className="ayuda-contextual-popover" role="dialog" aria-label={`Ayuda: ${ayuda.titulo}`}>
          <div className="ayuda-contextual-header">
            <span className="ayuda-contextual-titulo">{ayuda.titulo}</span>
            <button className="ayuda-contextual-cerrar" onClick={() => setAbierto(false)} aria-label="Cerrar ayuda">
              <FiX />
            </button>
          </div>
          <p className="ayuda-contextual-texto">{ayuda.texto}</p>
        </div>
      )}
    </>
  )
}

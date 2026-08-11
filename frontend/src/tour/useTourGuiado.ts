import { useEffect, useState } from 'react'

function claveTourCompletado(usuarioId: number): string {
  return `tour_completado_${usuarioId}`
}

/**
 * Controla si el modal del tour debe mostrarse: automáticamente la primera
 * vez que un usuario entra (si no tiene la clave en localStorage), o de
 * forma manual vía relanzarTour() (botón "?" del header) sin importar si
 * ya se vio antes.
 */
export function useTourGuiado(usuarioId: number) {
  const [abierto, setAbierto] = useState(false)

  useEffect(() => {
    const yaVisto = localStorage.getItem(claveTourCompletado(usuarioId)) === 'true'
    if (!yaVisto) setAbierto(true)
  }, [usuarioId])

  function cerrarTour() {
    localStorage.setItem(claveTourCompletado(usuarioId), 'true')
    setAbierto(false)
  }

  function relanzarTour() {
    setAbierto(true)
  }

  return { abierto, cerrarTour, relanzarTour }
}

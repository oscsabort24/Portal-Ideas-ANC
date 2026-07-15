import { useEffect, useRef, useState } from 'react'

const AVISO_MS = 8 * 60 * 1000
const LIMITE_MS = 10 * 60 * 1000
// No reacciona a cada evento individual (mousemove dispara decenas de veces
// por segundo) — solo revisa el tiempo transcurrido cada cierto intervalo.
const INTERVALO_CHEQUEO_MS = 10_000

const EVENTOS_ACTIVIDAD = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'] as const

/**
 * Cierra la sesión automáticamente tras 30 minutos sin actividad de mouse/
 * teclado, con un aviso a los 25 minutos. Cualquier actividad reinicia
 * ambos umbrales (comparten el mismo timestamp base) y oculta el aviso si
 * estaba visible.
 */
export function useInactividad(onExpirar: () => void) {
  const ultimaActividadRef = useRef(Date.now())
  const [mostrarAviso, setMostrarAviso] = useState(false)

  useEffect(() => {
    function marcarActividad() {
      ultimaActividadRef.current = Date.now()
      setMostrarAviso(false)
    }

    EVENTOS_ACTIVIDAD.forEach((evento) => window.addEventListener(evento, marcarActividad))

    const intervalo = setInterval(() => {
      const inactivoMs = Date.now() - ultimaActividadRef.current
      if (inactivoMs >= LIMITE_MS) {
        onExpirar()
      } else if (inactivoMs >= AVISO_MS) {
        setMostrarAviso(true)
      }
    }, INTERVALO_CHEQUEO_MS)

    return () => {
      EVENTOS_ACTIVIDAD.forEach((evento) => window.removeEventListener(evento, marcarActividad))
      clearInterval(intervalo)
    }
  }, [onExpirar])

  return { mostrarAviso }
}

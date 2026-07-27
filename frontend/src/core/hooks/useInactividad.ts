import { useEffect, useRef, useState } from 'react'

const AVISO_MS = 20 * 60 * 1000
const LIMITE_MS = 25 * 60 * 1000
// No reacciona a cada evento individual (mousemove dispara decenas de veces
// por segundo) — solo revisa el tiempo transcurrido cada cierto intervalo.
const INTERVALO_CHEQUEO_MS = 10_000

const EVENTOS_ACTIVIDAD = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'] as const

/**
 * Cierra la sesión automáticamente tras 25 minutos sin actividad de mouse/
 * teclado, con un aviso a los 20 minutos. Cualquier actividad reinicia
 * ambos umbrales (comparten el mismo timestamp base) y oculta el aviso si
 * estaba visible.
 */
export function useInactividad(onExpirar: () => void) {
  const ultimaActividadRef = useRef(Date.now())
  // Una vez disparado el cierre de sesión, no se vuelve a disparar: el
  // intervalo sigue corriendo hasta que la navegación del logout desmonta
  // el componente, y sin este guard cada tick (10s) llamaba otra vez a
  // onExpirar() -> logoutRedirect() en bucle.
  const yaExpiroRef = useRef(false)
  const [mostrarAviso, setMostrarAviso] = useState(false)

  useEffect(() => {
    function marcarActividad() {
      // Después de expirar, la actividad ya no cuenta: la sesión está
      // cerrándose y reiniciar el contador solo reabriría la ventana de
      // aviso sobre una sesión que ya no existe.
      if (yaExpiroRef.current) return
      ultimaActividadRef.current = Date.now()
      setMostrarAviso(false)
    }

    EVENTOS_ACTIVIDAD.forEach((evento) => window.addEventListener(evento, marcarActividad))

    const intervalo = setInterval(() => {
      if (yaExpiroRef.current) return
      const inactivoMs = Date.now() - ultimaActividadRef.current
      if (inactivoMs >= LIMITE_MS) {
        yaExpiroRef.current = true
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

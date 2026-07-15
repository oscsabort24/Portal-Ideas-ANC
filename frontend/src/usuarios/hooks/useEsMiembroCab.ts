import { useEffect, useState } from 'react'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { listarMiembrosCab } from '../api'
import type { TipoCAB } from '../types'

/**
 * Resuelve las membresías de CAB del usuario actual (client-side, no hay
 * endpoint dedicado "mis membresías" — se filtra la lista completa por
 * usuario_id, igual que ya hacía ColaComite.tsx).
 *
 * Compartido entre ColaComite.tsx (para saber a qué colas tiene acceso) y
 * Sidebar.tsx (para decidir si mostrar el link "Cola del comité"), para no
 * duplicar esta lógica en dos lugares.
 */
export function useEsMiembroCab() {
  const usuarioActual = useUsuarioActual()
  const [tiposCab, setTiposCab] = useState<TipoCAB[] | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    listarMiembrosCab()
      .then((membresias) => {
        if (cancelado) return
        setTiposCab(membresias.filter((m) => m.usuario_id === usuarioActual.id).map((m) => m.tipo_cab))
      })
      .catch((err) => {
        if (cancelado) return
        setError(err instanceof Error ? err.message : 'No se pudieron cargar tus membresías de CAB')
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [usuarioActual.id])

  return {
    tiposCab,
    esMiembro: (tiposCab?.length ?? 0) > 0,
    cargando,
    error,
  }
}

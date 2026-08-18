import { useEffect, useState } from 'react'
import { misPermisos } from '../api'

/**
 * Permisos efectivos del usuario actual, resueltos por el backend
 * (permisos/service.py:permisos_efectivos) — reemplaza los chequeos de rol
 * hardcodeados que antes hacía el frontend directamente (ver
 * diseno-pendiente/fase-permisos-por-rol.md.preview).
 */
export function useMisPermisos() {
  const [veTodasLasIdeas, setVeTodasLasIdeas] = useState(false)
  const [veFlowControl, setVeFlowControl] = useState(false)
  const [esRevisorElegible, setEsRevisorElegible] = useState(false)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let cancelado = false
    misPermisos()
      .then((permisos) => {
        if (cancelado) return
        setVeTodasLasIdeas(Boolean(permisos.ve_todas_las_ideas))
        setVeFlowControl(Boolean(permisos.ve_flow_control))
        setEsRevisorElegible(Boolean(permisos.es_revisor_elegible))
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [])

  return { veTodasLasIdeas, veFlowControl, esRevisorElegible, cargando }
}

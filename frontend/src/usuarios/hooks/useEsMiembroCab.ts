import { useEffect, useState } from 'react'
import { misDepartamentos } from '../../comites/api'
import type { DepartamentoVisible } from '../../comites/types'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { listarMiembrosCab } from '../api'

/**
 * Resuelve si el usuario actual es miembro de algún CAB y qué
 * departamentos ve (ver comites/router.py:mis-departamentos, que ya
 * resuelve el filtro real en el backend — este hook solo decide si
 * mostrar la sección de CAB en el sidebar y el badge de departamentos).
 *
 * Ya no expone `tiposCab` — el filtro por tipo_cab desapareció con
 * CAB por departamento (ver diseno-pendiente/cab-departamento-reasignacion.md.preview).
 */
export function useEsMiembroCab() {
  const usuarioActual = useUsuarioActual()
  const [esMiembroCab, setEsMiembroCab] = useState<boolean | null>(null)
  const [departamentos, setDepartamentos] = useState<DepartamentoVisible[] | null>(null)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    Promise.all([listarMiembrosCab(), misDepartamentos()])
      .then(([membresias, deptos]) => {
        if (cancelado) return
        setEsMiembroCab(membresias.some((m) => m.usuario_id === usuarioActual.id))
        setDepartamentos(deptos)
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
    esMiembro: esMiembroCab ?? false,
    departamentos: departamentos ?? [],
    cargando,
    error,
  }
}

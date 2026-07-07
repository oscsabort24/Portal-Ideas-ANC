import { useEffect, useState } from 'react'
import { FiAward } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { listarMiembrosCab, listarUsuarios, quitarMiembroCab } from '../api'
import type { MiembroCABDetalle, TipoCAB, Usuario } from '../types'
import FormularioMiembroCAB from './FormularioMiembroCAB'

const NOMBRES_CAB: Record<TipoCAB, string> = {
  innovacion: 'CAB Innovación',
  transformacion_digital: 'CAB Transformación Digital',
}

export default function ListaMiembrosCAB() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [miembros, setMiembros] = useState<MiembroCABDetalle[]>([])
  const [personas, setPersonas] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listarMiembrosCab(), listarUsuarios()])
      .then(([m, p]) => {
        setMiembros(m)
        setPersonas(p)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los comités'))
      .finally(() => setCargando(false))
  }, [])

  async function handleQuitar(miembro: MiembroCABDetalle) {
    const confirmado = window.confirm(
      `¿Quitar a ${miembro.usuario.nombre} del ${NOMBRES_CAB[miembro.tipo_cab]}?`
    )
    if (!confirmado) return
    try {
      await quitarMiembroCab(miembro.id)
      setMiembros((prev) => prev.filter((m) => m.id !== miembro.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo quitar al miembro del comité')
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <FormularioMiembroCAB personas={personas} onAgregado={(m) => setMiembros((prev) => [...prev, m])} />
      {error && <p className="form-error">{error}</p>}

      {(['innovacion', 'transformacion_digital'] as TipoCAB[]).map((tipo) => (
        <div key={tipo} className="cab-grupo">
          <h2 className="cab-grupo-titulo">{NOMBRES_CAB[tipo]}</h2>
          <div className="lista-simple">
            {miembros.filter((m) => m.tipo_cab === tipo).length === 0 && (
              <p className="cab-vacio">Sin miembros asignados todavía.</p>
            )}
            {miembros
              .filter((m) => m.tipo_cab === tipo)
              .map((m) => (
                <div key={m.id} className="item-simple">
                  <FiAward className="item-simple-icon" />
                  {m.usuario.nombre}
                  <span className="item-simple-secundario">{m.usuario.correo}</span>
                  {esAdmin && (
                    <div className="item-simple-actions">
                      <button className="btn-small peligro" onClick={() => handleQuitar(m)}>
                        Quitar
                      </button>
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}

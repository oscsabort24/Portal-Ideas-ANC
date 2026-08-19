import { useEffect, useState } from 'react'
import { FiAward } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import {
  actualizarDepartamentosMiembroCab,
  listarDepartamentos,
  listarMiembrosCab,
  listarUsuarios,
  quitarMiembroCab,
} from '../api'
import type { Departamento, MiembroCABDetalle, TipoCAB, Usuario } from '../types'
import FormularioMiembroCAB from './FormularioMiembroCAB'

const NOMBRES_CAB: Record<TipoCAB, string> = {
  innovacion: 'CAB Innovación',
  transformacion_digital: 'CAB Transformación Digital',
}

function SelectorDepartamentos({
  miembro,
  departamentos,
  onGuardado,
}: {
  miembro: MiembroCABDetalle
  departamentos: Departamento[]
  onGuardado: (actualizado: MiembroCABDetalle) => void
}) {
  const [seleccion, setSeleccion] = useState<number[]>(miembro.departamentos.map((d) => d.id))
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function alternar(id: number) {
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))
  }

  async function guardar() {
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarDepartamentosMiembroCab(miembro.id, { departamento_ids: seleccion })
      onGuardado(actualizado)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron guardar los departamentos')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="item-simple-detalle" style={{ marginTop: 6 }}>
      <p className="form-help" style={{ marginBottom: 4 }}>
        Departamentos que ve (sin ninguno seleccionado = ve todos):
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
        {departamentos.map((d) => (
          <label key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={seleccion.includes(d.id)} onChange={() => alternar(d.id)} />
            {d.nombre}
          </label>
        ))}
      </div>
      {error && <p className="form-error">{error}</p>}
      <button className="btn-small" onClick={guardar} disabled={guardando}>
        {guardando ? 'Guardando...' : 'Guardar departamentos'}
      </button>
    </div>
  )
}

export default function ListaMiembrosCAB() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [miembros, setMiembros] = useState<MiembroCABDetalle[]>([])
  const [personas, setPersonas] = useState<Usuario[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listarMiembrosCab(), listarUsuarios(), listarDepartamentos()])
      .then(([m, p, d]) => {
        setMiembros(m)
        setPersonas(p)
        setDepartamentos(d)
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

  function handleDepartamentosGuardados(actualizado: MiembroCABDetalle) {
    setMiembros((prev) => prev.map((m) => (m.id === actualizado.id ? actualizado : m)))
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
                <div key={m.id} className="item-simple" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
                  {esAdmin && (
                    <SelectorDepartamentos
                      miembro={m}
                      departamentos={departamentos}
                      onGuardado={handleDepartamentosGuardados}
                    />
                  )}
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}

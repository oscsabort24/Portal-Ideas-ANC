import { useEffect, useMemo, useState } from 'react'
import { FiBriefcase } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import {
  actualizarPuesto,
  actualizarPuestoUnico,
  eliminarPuesto,
  listarDepartamentos,
  listarPuestos,
} from '../api'
import type { Departamento, Puesto } from '../types'
import FormularioPuesto from './FormularioPuesto'

export default function ListaPuestos() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [puestos, setPuestos] = useState<Puesto[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [departamentoFiltro, setDepartamentoFiltro] = useState('')
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [departamentoEditado, setDepartamentoEditado] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    Promise.all([listarPuestos(), listarDepartamentos()])
      .then(([p, d]) => {
        setPuestos(p)
        setDepartamentos(d)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los puestos'))
      .finally(() => setCargando(false))
  }, [])

  function nombreDepartamento(id: number): string {
    return departamentos.find((d) => d.id === id)?.nombre ?? '—'
  }

  function iniciarEdicion(p: Puesto) {
    setEditandoId(p.id)
    setNombreEditado(p.nombre)
    setDepartamentoEditado(String(p.departamento_id))
  }

  async function guardarEdicion(id: number) {
    if (!nombreEditado.trim() || !departamentoEditado) return
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarPuesto(id, {
        nombre: nombreEditado.trim(),
        departamento_id: Number(departamentoEditado),
      })
      setPuestos((prev) => prev.map((p) => (p.id === id ? actualizado : p)))
      setEditandoId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el puesto')
    } finally {
      setGuardando(false)
    }
  }

  async function handleToggleUnico(p: Puesto) {
    setError(null)
    try {
      const actualizado = await actualizarPuestoUnico(p.id, !p.es_unico_por_pais)
      setPuestos((prev) => prev.map((x) => (x.id === p.id ? actualizado : x)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el puesto')
    }
  }

  async function handleEliminar(p: Puesto) {
    const confirmado = window.confirm(`¿Eliminar el puesto "${p.nombre}"?`)
    if (!confirmado) return
    setError(null)
    try {
      await eliminarPuesto(p.id)
      setPuestos((prev) => prev.filter((x) => x.id !== p.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el puesto')
    }
  }

  const puestosFiltrados = useMemo(() => {
    if (!departamentoFiltro) return puestos
    return puestos.filter((p) => p.departamento_id === Number(departamentoFiltro))
  }, [puestos, departamentoFiltro])

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <FormularioPuesto departamentos={departamentos} onCreado={(p) => setPuestos((prev) => [...prev, p])} />
      {error && <p className="form-error">{error}</p>}

      <div className="form-row filtros-personas">
        <div className="form-field">
          <label className="form-label" htmlFor="filtro-departamento-puesto">Departamento</label>
          <select
            id="filtro-departamento-puesto"
            className="form-input"
            value={departamentoFiltro}
            onChange={(e) => setDepartamentoFiltro(e.target.value)}
          >
            <option value="">Todos los departamentos</option>
            {departamentos.map((d) => (
              <option key={d.id} value={d.id}>{d.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      {puestosFiltrados.length === 0 ? (
        <p className="cab-vacio">No hay puestos para este filtro.</p>
      ) : (
        <div className="lista-simple">
          {puestosFiltrados.map((p) =>
            editandoId === p.id ? (
              <div key={p.id} className="item-simple">
                <FiBriefcase className="item-simple-icon" />
                <input
                  className="item-simple-edit-input"
                  value={nombreEditado}
                  onChange={(e) => setNombreEditado(e.target.value)}
                  autoFocus
                />
                <select
                  className="form-input"
                  style={{ maxWidth: 220 }}
                  value={departamentoEditado}
                  onChange={(e) => setDepartamentoEditado(e.target.value)}
                >
                  {departamentos.map((d) => (
                    <option key={d.id} value={d.id}>{d.nombre}</option>
                  ))}
                </select>
                <div className="item-simple-actions">
                  <button
                    className="btn-small exito"
                    onClick={() => guardarEdicion(p.id)}
                    disabled={!nombreEditado.trim() || !departamentoEditado || guardando}
                  >
                    {guardando ? 'Guardando...' : 'Guardar'}
                  </button>
                  <button className="btn-small" onClick={() => setEditandoId(null)}>
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div key={p.id} className="item-simple">
                <FiBriefcase className="item-simple-icon" />
                {p.nombre}
                <span className="item-simple-secundario">{nombreDepartamento(p.departamento_id)}</span>
                <div className="item-simple-actions">
                  {p.es_unico_por_pais && <span className="rol-badge">Único por país</span>}
                  {esAdmin && (
                    <>
                      <button className="btn-small" onClick={() => iniciarEdicion(p)}>
                        Editar
                      </button>
                      <button
                        className={`btn-small ${p.es_unico_por_pais ? 'peligro' : 'exito'}`}
                        onClick={() => handleToggleUnico(p)}
                      >
                        {p.es_unico_por_pais ? 'Desmarcar único' : 'Marcar único'}
                      </button>
                      <button className="btn-small peligro" onClick={() => handleEliminar(p)}>
                        Eliminar
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}

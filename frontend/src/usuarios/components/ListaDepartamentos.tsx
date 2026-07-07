import { useEffect, useState } from 'react'
import { FiBriefcase } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { actualizarDepartamento, eliminarDepartamento, listarDepartamentos } from '../api'
import type { Departamento } from '../types'
import FormularioDepartamento from './FormularioDepartamento'

export default function ListaDepartamentos() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [nombreEditado, setNombreEditado] = useState('')
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    listarDepartamentos()
      .then(setDepartamentos)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los departamentos'))
      .finally(() => setCargando(false))
  }, [])

  function iniciarEdicion(d: Departamento) {
    setEditandoId(d.id)
    setNombreEditado(d.nombre)
  }

  async function guardarEdicion(id: number) {
    if (!nombreEditado.trim()) return
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarDepartamento(id, { nombre: nombreEditado.trim() })
      setDepartamentos((prev) => prev.map((d) => (d.id === id ? actualizado : d)))
      setEditandoId(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el departamento')
    } finally {
      setGuardando(false)
    }
  }

  async function handleEliminar(d: Departamento) {
    const confirmado = window.confirm(`¿Eliminar el departamento "${d.nombre}"?`)
    if (!confirmado) return
    setError(null)
    try {
      await eliminarDepartamento(d.id)
      setDepartamentos((prev) => prev.filter((dep) => dep.id !== d.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo eliminar el departamento')
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <FormularioDepartamento onCreado={(dep) => setDepartamentos((prev) => [...prev, dep])} />
      {error && <p className="form-error">{error}</p>}

      <div className="lista-simple">
        {departamentos.map((d) =>
          editandoId === d.id ? (
            <div key={d.id} className="item-simple">
              <FiBriefcase className="item-simple-icon" />
              <input
                className="item-simple-edit-input"
                value={nombreEditado}
                onChange={(e) => setNombreEditado(e.target.value)}
                autoFocus
              />
              <div className="item-simple-actions">
                <button
                  className="btn-small exito"
                  onClick={() => guardarEdicion(d.id)}
                  disabled={!nombreEditado.trim() || guardando}
                >
                  {guardando ? 'Guardando...' : 'Guardar'}
                </button>
                <button className="btn-small" onClick={() => setEditandoId(null)}>
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <div key={d.id} className="item-simple">
              <FiBriefcase className="item-simple-icon" />
              {d.nombre}
              {esAdmin && (
                <div className="item-simple-actions">
                  <button className="btn-small" onClick={() => iniciarEdicion(d)}>
                    Editar
                  </button>
                  <button className="btn-small peligro" onClick={() => handleEliminar(d)}>
                    Eliminar
                  </button>
                </div>
              )}
            </div>
          )
        )}
      </div>
    </div>
  )
}

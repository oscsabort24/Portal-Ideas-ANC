import { useEffect, useState } from 'react'
import { FiAlertCircle } from 'react-icons/fi'
import { listarUsuarios } from '../../usuarios/api'
import type { Usuario } from '../../usuarios/types'
import { asignarRevisor, revisionesSinAsignar } from '../api'
import type { RevisionDetalle } from '../types'

export default function IdeasSinAsignar() {
  const [revisiones, setRevisiones] = useState<RevisionDetalle[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [seleccion, setSeleccion] = useState<Record<number, string>>({})
  const [enviandoId, setEnviandoId] = useState<number | null>(null)

  useEffect(() => {
    Promise.all([revisionesSinAsignar(), listarUsuarios()])
      .then(([r, u]) => {
        setRevisiones(r)
        setUsuarios(u)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las ideas sin asignar'))
      .finally(() => setCargando(false))
  }, [])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  // encargado_area, gerente y admin estan todos habilitados para revisar.
  const encargadosActivos = usuarios.filter(
    (u) => (u.rol === 'encargado_area' || u.rol === 'gerente' || u.rol === 'admin') && u.activo,
  )

  async function handleAsignar(revision: RevisionDetalle) {
    const revisorId = seleccion[revision.id]
    if (!revisorId) return
    setEnviandoId(revision.id)
    setError(null)
    try {
      await asignarRevisor(revision.idea_id, Number(revisorId))
      setRevisiones((prev) => prev.filter((r) => r.id !== revision.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo asignar la idea')
    } finally {
      setEnviandoId(null)
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      {error && <p className="form-error">{error}</p>}

      {revisiones.length === 0 ? (
        <p className="cab-vacio">No hay ideas pendientes de asignación.</p>
      ) : (
        <div className="tabla-personas">
          {revisiones.map((r) => (
            <div key={r.id} className="idea-card idea-card-borrador">
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiAlertCircle className="idea-card-icon idea-card-icon-borrador" />
                  <div>
                    <div className="idea-card-title">{r.idea.titulo}</div>
                    <div className="idea-card-date">
                      De {nombreAutor(r.idea.autor_id)} — sin encargado de área en su departamento
                    </div>
                  </div>
                </div>
              </div>

              <div className="form-row" style={{ marginTop: 12 }}>
                <select
                  className="form-input"
                  value={seleccion[r.id] ?? ''}
                  onChange={(e) => setSeleccion((prev) => ({ ...prev, [r.id]: e.target.value }))}
                >
                  <option value="">Selecciona un encargado de área</option>
                  {encargadosActivos.map((u) => (
                    <option key={u.id} value={u.id}>{u.nombre}</option>
                  ))}
                </select>
                <button
                  className="btn-primary"
                  disabled={!seleccion[r.id] || enviandoId === r.id}
                  onClick={() => handleAsignar(r)}
                >
                  {enviandoId === r.id ? 'Asignando...' : 'Asignar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

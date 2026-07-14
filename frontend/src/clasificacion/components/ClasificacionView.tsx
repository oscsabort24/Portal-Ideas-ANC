import { useEffect, useState } from 'react'
import { FiFileText } from 'react-icons/fi'
import { listarUsuarios } from '../../usuarios/api'
import type { TipoCAB, Usuario } from '../../usuarios/types'
import { clasificacionesPendientes, clasificar } from '../api'
import type { ClasificacionDetalle } from '../types'

const ETIQUETA_TIPO_CAB: Record<TipoCAB, string> = {
  innovacion: 'Innovación',
  transformacion_digital: 'Transformación Digital',
}

export default function ClasificacionView() {
  const [clasificaciones, setClasificaciones] = useState<ClasificacionDetalle[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [enviandoId, setEnviandoId] = useState<number | null>(null)

  useEffect(() => {
    Promise.all([clasificacionesPendientes(), listarUsuarios()])
      .then(([c, u]) => {
        setClasificaciones(c)
        setUsuarios(u)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las ideas pendientes'))
      .finally(() => setCargando(false))
  }, [])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  async function handleClasificar(c: ClasificacionDetalle, tipo: TipoCAB) {
    const confirmado = window.confirm(`¿Clasificar "${c.idea.titulo}" como ${ETIQUETA_TIPO_CAB[tipo]}?`)
    if (!confirmado) return
    setEnviandoId(c.id)
    setError(null)
    try {
      await clasificar(c.idea_id, tipo)
      setClasificaciones((prev) => prev.filter((x) => x.id !== c.id))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo clasificar la idea')
    } finally {
      setEnviandoId(null)
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <h1 className="page-title">Clasificación</h1>

      {error && <p className="form-error">{error}</p>}

      {clasificaciones.length === 0 ? (
        <p className="cab-vacio">No hay ideas pendientes de clasificar.</p>
      ) : (
        <div className="tabla-personas">
          {clasificaciones.map((c) => (
            <div key={c.id} className="idea-card idea-card-enviada">
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiFileText className="idea-card-icon idea-card-icon-enviada" />
                  <div>
                    <div className="idea-card-title">{c.idea.titulo}</div>
                    <div className="idea-card-date">
                      De {nombreAutor(c.idea.autor_id)} — aprobada el{' '}
                      {new Date(c.creado_en).toLocaleDateString('es-CR')}
                    </div>
                  </div>
                </div>
              </div>

              <div className="persona-card-actions" style={{ marginTop: 12 }}>
                <button
                  className="btn-small exito"
                  disabled={enviandoId === c.id}
                  onClick={() => handleClasificar(c, 'innovacion')}
                >
                  Innovación
                </button>
                <button
                  className="btn-small exito"
                  disabled={enviandoId === c.id}
                  onClick={() => handleClasificar(c, 'transformacion_digital')}
                >
                  Transformación Digital
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

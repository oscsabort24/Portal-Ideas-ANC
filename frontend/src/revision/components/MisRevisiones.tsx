import { useEffect, useState } from 'react'
import { FiFileText } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import DocumentosGenerados from '../../documentos/components/DocumentosGenerados'
import ResumenYPreguntas from '../../ideas/components/ResumenYPreguntas'
import { listarUsuarios, rolesConPermiso } from '../../usuarios/api'
import type { Usuario } from '../../usuarios/types'
import { aceptarReasignacion, aprobar, misRevisiones, pedirCambios, reasignar, rechazarReasignacion } from '../api'
import type { RevisionDetalle } from '../types'

type AccionAbierta = { revisionId: number; tipo: 'cambios' | 'reasignar' | 'rechazar-reasignacion' } | null

export default function MisRevisiones() {
  const usuarioActual = useUsuarioActual()
  const [revisiones, setRevisiones] = useState<RevisionDetalle[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [rolesElegibles, setRolesElegibles] = useState<string[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accionAbierta, setAccionAbierta] = useState<AccionAbierta>(null)
  const [retroalimentacion, setRetroalimentacion] = useState('')
  const [nuevoRevisorId, setNuevoRevisorId] = useState('')
  const [enviando, setEnviando] = useState(false)

  function cargar() {
    setCargando(true)
    setError(null)
    Promise.all([misRevisiones(), listarUsuarios()])
      .then(([r, u]) => {
        setRevisiones(r)
        setUsuarios(u)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar tus revisiones'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])
  useEffect(() => {
    rolesConPermiso('es_revisor_elegible').then(setRolesElegibles)
  }, [])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  // Roles habilitados para revisar (permiso configurable es_revisor_elegible,
  // ver diseno-pendiente/fase-permisos-por-rol.md.preview — admin ya viene
  // incluido en rolesElegibles por bypass del backend).
  const encargadosActivos = usuarios.filter(
    (u) => rolesElegibles.includes(u.rol) && u.activo && u.id !== usuarioActual.id,
  )

  function cerrarAccion() {
    setAccionAbierta(null)
    setRetroalimentacion('')
    setNuevoRevisorId('')
  }

  async function handleAprobar(ideaId: number) {
    const confirmado = window.confirm('¿Aprobar esta idea?')
    if (!confirmado) return
    setError(null)
    try {
      await aprobar(ideaId)
      setRevisiones((prev) => prev.filter((r) => r.idea_id !== ideaId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo aprobar la idea')
    }
  }

  async function handlePedirCambios(ideaId: number) {
    if (!retroalimentacion.trim()) return
    setEnviando(true)
    setError(null)
    try {
      await pedirCambios(ideaId, retroalimentacion.trim())
      setRevisiones((prev) => prev.filter((r) => r.idea_id !== ideaId))
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar la retroalimentación')
    } finally {
      setEnviando(false)
    }
  }

  async function handleReasignar(ideaId: number) {
    if (!nuevoRevisorId) return
    setEnviando(true)
    setError(null)
    try {
      await reasignar(ideaId, Number(nuevoRevisorId))
      // Ya no se ejecuta de inmediato — queda propuesta, esperando que la
      // persona destino acepte o rechace. Sigue apareciendo en esta lista
      // (revisor_id no cambió), solo cambia de estado.
      cargar()
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo proponer la reasignación')
    } finally {
      setEnviando(false)
    }
  }

  async function handleAceptarReasignacion(ideaId: number) {
    setEnviando(true)
    setError(null)
    try {
      await aceptarReasignacion(ideaId)
      cargar()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo aceptar la reasignación')
    } finally {
      setEnviando(false)
    }
  }

  async function handleRechazarReasignacion(ideaId: number) {
    if (!retroalimentacion.trim()) return
    setEnviando(true)
    setError(null)
    try {
      await rechazarReasignacion(ideaId, retroalimentacion.trim())
      cargar()
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo rechazar la reasignación')
    } finally {
      setEnviando(false)
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      {error && <p className="form-error">{error}</p>}

      {revisiones.length === 0 ? (
        <p className="cab-vacio">No tienes ideas pendientes de revisión.</p>
      ) : (
        <div className="tabla-personas">
          {revisiones.map((r) => (
            <div key={r.id} className="idea-card idea-card-enviada">
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiFileText className="idea-card-icon idea-card-icon-enviada" />
                  <div>
                    <div className="idea-card-title">
                      {r.idea.titulo}
                      {r.revisor_id !== null && r.revisor_id !== usuarioActual.id && (
                        <span className="idea-estado-badge" style={{ marginLeft: 8 }}>
                          Asignada a: {r.revisor?.nombre ?? '—'}
                        </span>
                      )}
                      {r.estado === 'pendiente_aceptacion_reasignacion' && r.propuesto_a_id === usuarioActual.id && (
                        <span className="idea-estado-badge" style={{ marginLeft: 8 }}>
                          Requiere tu respuesta
                        </span>
                      )}
                    </div>
                    <div className="idea-card-date">
                      De {nombreAutor(r.idea.autor_id)} — enviada el{' '}
                      {r.idea.fecha_envio ? new Date(r.idea.fecha_envio).toLocaleDateString('es-CR') : '—'}
                    </div>
                  </div>
                </div>
              </div>

              <ResumenYPreguntas ideaId={r.idea_id} origen="revision" />

              <DocumentosGenerados ideaId={r.idea_id} />

              {accionAbierta?.revisionId === r.id && accionAbierta.tipo === 'cambios' && (
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="form-label" htmlFor={`retro-${r.id}`}>Retroalimentación</label>
                  <textarea
                    id={`retro-${r.id}`}
                    className="form-input"
                    rows={3}
                    value={retroalimentacion}
                    onChange={(e) => setRetroalimentacion(e.target.value)}
                    placeholder="Explica qué cambios necesita esta idea..."
                  />
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!retroalimentacion.trim() || enviando}
                      onClick={() => handlePedirCambios(r.idea_id)}
                    >
                      {enviando ? 'Enviando...' : 'Enviar retroalimentación'}
                    </button>
                    <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                  </div>
                </div>
              )}

              {r.estado === 'pendiente_aceptacion_reasignacion' && r.propuesto_a_id === usuarioActual.id && (
                <div className="persona-card-actions" style={{ marginTop: 12 }}>
                  {accionAbierta?.revisionId === r.id && accionAbierta.tipo === 'rechazar-reasignacion' ? (
                    <div className="form-field">
                      <label className="form-label" htmlFor={`motivo-rechazo-${r.id}`}>Motivo del rechazo</label>
                      <textarea
                        id={`motivo-rechazo-${r.id}`}
                        className="form-input"
                        rows={3}
                        value={retroalimentacion}
                        onChange={(e) => setRetroalimentacion(e.target.value)}
                        placeholder="Por qué no podés atender esta idea..."
                      />
                      <div className="form-row" style={{ marginTop: 10 }}>
                        <button
                          className="btn-primary"
                          disabled={!retroalimentacion.trim() || enviando}
                          onClick={() => handleRechazarReasignacion(r.idea_id)}
                        >
                          {enviando ? 'Enviando...' : 'Confirmar rechazo'}
                        </button>
                        <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <button className="btn-small exito" onClick={() => handleAceptarReasignacion(r.idea_id)}>
                        Aceptar
                      </button>
                      <button
                        className="btn-small peligro"
                        onClick={() => setAccionAbierta({ revisionId: r.id, tipo: 'rechazar-reasignacion' })}
                      >
                        Rechazar
                      </button>
                    </>
                  )}
                </div>
              )}

              {accionAbierta?.revisionId === r.id && accionAbierta.tipo === 'reasignar' && (
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="form-label" htmlFor={`reasignar-${r.id}`}>Reasignar a</label>
                  <select
                    id={`reasignar-${r.id}`}
                    className="form-input"
                    value={nuevoRevisorId}
                    onChange={(e) => setNuevoRevisorId(e.target.value)}
                  >
                    <option value="">Selecciona un encargado de área</option>
                    {encargadosActivos.map((u) => (
                      <option key={u.id} value={u.id}>{u.nombre}</option>
                    ))}
                  </select>
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!nuevoRevisorId || enviando}
                      onClick={() => handleReasignar(r.idea_id)}
                    >
                      {enviando ? 'Reasignando...' : 'Confirmar reasignación'}
                    </button>
                    <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                  </div>
                </div>
              )}

              {!accionAbierta && r.estado === 'pendiente_revision' && (
                <div className="persona-card-actions" style={{ marginTop: 12 }}>
                  <button className="btn-small exito" onClick={() => handleAprobar(r.idea_id)}>
                    Aprobar
                  </button>
                  <button
                    className="btn-small"
                    onClick={() => setAccionAbierta({ revisionId: r.id, tipo: 'cambios' })}
                  >
                    Pedir cambios
                  </button>
                  <button
                    className="btn-small"
                    onClick={() => setAccionAbierta({ revisionId: r.id, tipo: 'reasignar' })}
                  >
                    Reasignar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

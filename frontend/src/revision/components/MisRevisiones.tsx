import { useEffect, useState } from 'react'
import { FiFileText, FiXCircle } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import DocumentosGenerados from '../../documentos/components/DocumentosGenerados'
import ResumenYPreguntas from '../../ideas/components/ResumenYPreguntas'
import { listarUsuariosDirectorioBasico } from '../../usuarios/api'
import type { UsuarioBasico } from '../../usuarios/types'
import {
  aceptarReasignacion,
  aprobar,
  candidatosReasignar,
  misRevisiones,
  pedirCambios,
  reasignar,
  rechazadasEnComite,
  rechazar,
  rechazarReasignacion,
} from '../api'
import type { RevisionDetalle, RevisionRechazadaEnComite } from '../types'
import { ayudaMotivo, motivoValido } from '../../core/motivoRechazo'

type AccionAbierta = { revisionId: number; tipo: 'cambios' | 'reasignar' | 'rechazar' | 'rechazar-reasignacion' } | null

/**
 * Ideas que este revisor aprobó y que el comité rechazó después.
 *
 * Existe porque al aprobar, la idea sale de misRevisiones() —que solo trae lo
 * pendiente— y nada vuelve a traer al encargado de área a ella. El motivo del
 * rechazo quedaba únicamente en la línea de tiempo de la idea, que él no
 * tiene por qué abrir. Se muestra el motivo acá mismo, no un link.
 *
 * Se oculta entera si no hay ninguna: es un aviso, no una sección fija que
 * ocupe espacio con un "no hay nada" permanente.
 */
function SeccionRechazadasEnComite() {
  const [items, setItems] = useState<RevisionRechazadaEnComite[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    rechazadasEnComite()
      .then(setItems)
      // Un fallo acá no puede tumbar la pantalla de revisiones, que es el
      // trabajo real de la persona: se avisa y se sigue.
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las ideas rechazadas en comité'))
  }, [])

  if (error) return <p className="form-error">{error}</p>
  if (items.length === 0) return null

  return (
    <div className="rechazadas-comite">
      <h2 className="rechazadas-comite-titulo">
        Rechazadas en comité
        <span className="rechazadas-comite-conteo">{items.length}</span>
      </h2>
      <p className="form-help" style={{ marginTop: -4 }}>
        Ideas que aprobaste y que el comité decidió no avanzar.
      </p>

      {items.map((r) => (
        <div key={r.idea.id} className="rechazadas-comite-card">
          <div className="rechazadas-comite-encabezado">
            <FiXCircle className="rechazadas-comite-icono" />
            <div>
              <div className="idea-card-title">{r.idea.titulo}</div>
              <div className="idea-card-date">
                {r.rechazada_por ? `Rechazada por ${r.rechazada_por.nombre}` : 'Rechazada por el comité'}
                {r.fecha_resolucion && ` — ${new Date(r.fecha_resolucion).toLocaleDateString('es-CR')}`}
              </div>
            </div>
          </div>
          {r.motivo_rechazo && (
            <blockquote className="rechazadas-comite-motivo">{r.motivo_rechazo}</blockquote>
          )}
        </div>
      ))}
    </div>
  )
}

export default function MisRevisiones() {
  const usuarioActual = useUsuarioActual()
  const [revisiones, setRevisiones] = useState<RevisionDetalle[]>([])
  const [usuarios, setUsuarios] = useState<UsuarioBasico[]>([])
  const [candidatos, setCandidatos] = useState<UsuarioBasico[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accionAbierta, setAccionAbierta] = useState<AccionAbierta>(null)
  const [retroalimentacion, setRetroalimentacion] = useState('')
  const [nuevoRevisorId, setNuevoRevisorId] = useState('')
  const [enviando, setEnviando] = useState(false)

  function cargar() {
    setCargando(true)
    setError(null)
    // directorio-basico (no listarUsuarios completo): esta pantalla la usan
    // encargados de área, no solo admin, y listarUsuarios() ahora requiere
    // admin (ver diagnóstico hallazgo #2, tanda 3) — solo se necesita el
    // nombre del autor para mostrarlo, nunca correo ni rol.
    Promise.all([misRevisiones(), listarUsuariosDirectorioBasico()])
      .then(([r, u]) => {
        setRevisiones(r)
        setUsuarios(u)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar tus revisiones'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  function abrirReasignar(revisionId: number, ideaId: number) {
    setAccionAbierta({ revisionId, tipo: 'reasignar' })
    // Filtro por rol+activo ya lo aplica el backend (ver
    // GET /revision/candidatos-reasignar/{idea_id}) — el picker solo
    // recibe id/nombre/departamento_id, nunca rol ni correo.
    candidatosReasignar(ideaId)
      .then(setCandidatos)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los candidatos'))
  }

  function cerrarAccion() {
    setAccionAbierta(null)
    setRetroalimentacion('')
    setNuevoRevisorId('')
    setCandidatos([])
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
    // Mismo mínimo que rechazar — el backend valida igual (core/rechazo.py).
    if (!motivoValido(retroalimentacion)) return
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

  async function handleRechazar(ideaId: number) {
    // Misma condición que habilita el botón — el backend igual valida y
    // devuelve 400 (core/rechazo.py), esto solo evita el viaje.
    if (!motivoValido(retroalimentacion)) return
    setEnviando(true)
    setError(null)
    try {
      await rechazar(ideaId, retroalimentacion.trim())
      setRevisiones((prev) => prev.filter((r) => r.idea_id !== ideaId))
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo rechazar la idea')
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

      <SeccionRechazadasEnComite />

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
                  {ayudaMotivo(retroalimentacion) && (
                    <p className="form-help">{ayudaMotivo(retroalimentacion)}</p>
                  )}
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!motivoValido(retroalimentacion) || enviando}
                      onClick={() => handlePedirCambios(r.idea_id)}
                    >
                      {enviando ? 'Enviando...' : 'Enviar retroalimentación'}
                    </button>
                    <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                  </div>
                </div>
              )}

              {accionAbierta?.revisionId === r.id && accionAbierta.tipo === 'rechazar' && (
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="form-label" htmlFor={`motivo-rechazo-idea-${r.id}`}>Motivo de rechazo</label>
                  <textarea
                    id={`motivo-rechazo-idea-${r.id}`}
                    className="form-input"
                    rows={3}
                    value={retroalimentacion}
                    onChange={(e) => setRetroalimentacion(e.target.value)}
                    placeholder="Explica por qué se rechaza esta idea..."
                  />
                  {ayudaMotivo(retroalimentacion) && (
                    <p className="form-help">{ayudaMotivo(retroalimentacion)}</p>
                  )}
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!motivoValido(retroalimentacion) || enviando}
                      onClick={() => handleRechazar(r.idea_id)}
                    >
                      {enviando ? 'Enviando...' : 'Confirmar rechazo'}
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
                    {candidatos.map((u) => (
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
                    onClick={() => abrirReasignar(r.id, r.idea_id)}
                  >
                    Reasignar
                  </button>
                  <button
                    className="btn-small peligro"
                    onClick={() => setAccionAbierta({ revisionId: r.id, tipo: 'rechazar' })}
                  >
                    Rechazar
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

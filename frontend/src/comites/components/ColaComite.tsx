import { useEffect, useState } from 'react'
import { FiFileText } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import DocumentosGenerados from '../../documentos/components/DocumentosGenerados'
import ResumenYPreguntas from '../../ideas/components/ResumenYPreguntas'
import { listarUsuariosDirectorioBasico } from '../../usuarios/api'
import { useEsMiembroCab } from '../../usuarios/hooks/useEsMiembroCab'
import type { UsuarioBasico } from '../../usuarios/types'
import {
  aceptarReasignacion,
  aprobar,
  candidatosReasignar,
  colaComite,
  rechazar,
  rechazarReasignacion,
  reasignar,
} from '../api'
import FormularioRice from './FormularioRice'
import type { ComiteIdeaDetalle } from '../types'

type AccionAbierta = { comiteId: number; tipo: 'motivo-rechazo' | 'reasignar' | 'rechazar-reasignacion' } | null

export default function ColaComite() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const { esMiembro, departamentos, cargando: cargandoMembresias, error: errorMembresias } = useEsMiembroCab()
  const [cola, setCola] = useState<ComiteIdeaDetalle[]>([])
  const [usuarios, setUsuarios] = useState<UsuarioBasico[]>([])
  const [candidatos, setCandidatos] = useState<UsuarioBasico[]>([])
  const [cargandoCola, setCargandoCola] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [accionAbierta, setAccionAbierta] = useState<AccionAbierta>(null)
  const [motivo, setMotivo] = useState('')
  const [nuevoAsignadoId, setNuevoAsignadoId] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [riceAbiertoPara, setRiceAbiertoPara] = useState<number | null>(null)

  useEffect(() => {
    // directorio-basico (no listarUsuarios completo): miembros de CAB no
    // son admin, y listarUsuarios() ahora requiere admin (ver diagnóstico
    // hallazgo #2, tanda 3) — solo se necesita el nombre del autor.
    listarUsuariosDirectorioBasico()
      .then(setUsuarios)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los usuarios'))
  }, [])

  function cargarCola() {
    setCargandoCola(true)
    setError(null)
    colaComite()
      .then(setCola)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la cola del comité'))
      .finally(() => setCargandoCola(false))
  }

  useEffect(cargarCola, [])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  function cerrarAccion() {
    setAccionAbierta(null)
    setMotivo('')
    setNuevoAsignadoId('')
    setCandidatos([])
  }

  async function handleAprobar(ideaId: number) {
    const confirmado = window.confirm('¿Aprobar esta idea?')
    if (!confirmado) return
    setError(null)
    try {
      await aprobar(ideaId)
      setCola((prev) => prev.filter((c) => c.idea_id !== ideaId))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo aprobar la idea')
    }
  }

  async function handleRechazar(ideaId: number) {
    if (!motivo.trim()) return
    setEnviando(true)
    setError(null)
    try {
      await rechazar(ideaId, motivo.trim())
      setCola((prev) => prev.filter((c) => c.idea_id !== ideaId))
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo rechazar la idea')
    } finally {
      setEnviando(false)
    }
  }

  async function handleReasignar(ideaId: number) {
    if (!nuevoAsignadoId) return
    setEnviando(true)
    setError(null)
    try {
      await reasignar(ideaId, Number(nuevoAsignadoId))
      cargarCola()
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
      cargarCola()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo aceptar la reasignación')
    } finally {
      setEnviando(false)
    }
  }

  async function handleRechazarReasignacion(ideaId: number) {
    if (!motivo.trim()) return
    setEnviando(true)
    setError(null)
    try {
      await rechazarReasignacion(ideaId, motivo.trim())
      cargarCola()
      cerrarAccion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo rechazar la reasignación')
    } finally {
      setEnviando(false)
    }
  }

  if (cargandoMembresias) return <p>Cargando...</p>

  if (!esAdmin && !esMiembro) {
    return (
      <div>
        <h1 className="page-title">Mis decisiones</h1>
        <p className="cab-vacio">No sos Portfolio Owner de ningún departamento.</p>
      </div>
    )
  }

  function abrirReasignar(comiteId: number, ideaId: number) {
    setAccionAbierta({ comiteId, tipo: 'reasignar' })
    // Filtro por activo ya lo aplica el backend (ver
    // GET /comites/candidatos-reasignar/{idea_id}) — mismo criterio que
    // tenía este filtro client-side (activo + no vos mismo, sin filtro de
    // rol/departamento: eso lo sigue validando _validar_miembro_destino al
    // confirmar). El picker solo recibe id/nombre/departamento_id.
    candidatosReasignar(ideaId)
      .then(setCandidatos)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los candidatos'))
  }

  return (
    <div>
      <h1 className="page-title">Mis decisiones</h1>

      {!esAdmin && (
        <p className="form-help">
          Viendo: {departamentos.length > 0 ? departamentos.map((d) => d.nombre).join(', ') : 'todos los departamentos'}
        </p>
      )}

      {(error || errorMembresias) && <p className="form-error">{error || errorMembresias}</p>}

      {cargandoCola ? (
        <p>Cargando...</p>
      ) : cola.length === 0 ? (
        <p className="cab-vacio">No hay ideas pendientes en esta cola.</p>
      ) : (
        <div className="tabla-personas">
          {cola.map((c, indice) => (
            <div key={c.id} className="idea-card idea-card-enviada">
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiFileText className="idea-card-icon idea-card-icon-enviada" />
                  <div>
                    <div className="idea-card-title">
                      #{indice + 1} — {c.idea.titulo}
                      {c.asignado_a && (
                        <span className="idea-estado-badge" style={{ marginLeft: 8 }}>
                          Asignada a: {c.asignado_a.nombre}
                        </span>
                      )}
                      {c.estado === 'pendiente_aceptacion_reasignacion' && c.propuesto_a_id === usuarioActual.id && (
                        <span className="idea-estado-badge" style={{ marginLeft: 8 }}>
                          Requiere tu respuesta
                        </span>
                      )}
                    </div>
                    <div className="idea-card-date">
                      De {nombreAutor(c.idea.autor_id)} — en cola desde{' '}
                      {new Date(c.creado_en).toLocaleDateString('es-CR')}
                    </div>
                  </div>
                </div>
              </div>

              <ResumenYPreguntas ideaId={c.idea_id} origen="comite" />
              <DocumentosGenerados ideaId={c.idea_id} />

              {c.estado === 'pendiente_aceptacion_reasignacion' && c.propuesto_a_id === usuarioActual.id ? (
                accionAbierta?.comiteId === c.id && accionAbierta.tipo === 'rechazar-reasignacion' ? (
                  <div className="form-field" style={{ marginTop: 12 }}>
                    <label className="form-label" htmlFor={`motivo-rechazo-reas-${c.id}`}>Motivo del rechazo</label>
                    <textarea
                      id={`motivo-rechazo-reas-${c.id}`}
                      className="form-input"
                      rows={3}
                      value={motivo}
                      onChange={(e) => setMotivo(e.target.value)}
                      placeholder="Por qué no podés atender esta idea..."
                    />
                    <div className="form-row" style={{ marginTop: 10 }}>
                      <button
                        className="btn-primary"
                        disabled={!motivo.trim() || enviando}
                        onClick={() => handleRechazarReasignacion(c.idea_id)}
                      >
                        {enviando ? 'Enviando...' : 'Confirmar rechazo'}
                      </button>
                      <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                    </div>
                  </div>
                ) : (
                  <div className="persona-card-actions" style={{ marginTop: 12 }}>
                    <button className="btn-small exito" onClick={() => handleAceptarReasignacion(c.idea_id)}>
                      Aceptar
                    </button>
                    <button
                      className="btn-small peligro"
                      onClick={() => setAccionAbierta({ comiteId: c.id, tipo: 'rechazar-reasignacion' })}
                    >
                      Rechazar
                    </button>
                  </div>
                )
              ) : c.estado !== 'pendiente' ? null : accionAbierta?.comiteId === c.id && accionAbierta.tipo === 'motivo-rechazo' ? (
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="form-label" htmlFor={`motivo-${c.id}`}>Motivo de rechazo</label>
                  <textarea
                    id={`motivo-${c.id}`}
                    className="form-input"
                    rows={3}
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Explica por qué se rechaza esta idea..."
                  />
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!motivo.trim() || enviando}
                      onClick={() => handleRechazar(c.idea_id)}
                    >
                      {enviando ? 'Enviando...' : 'Confirmar rechazo'}
                    </button>
                    <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                  </div>
                </div>
              ) : accionAbierta?.comiteId === c.id && accionAbierta.tipo === 'reasignar' ? (
                <div className="form-field" style={{ marginTop: 12 }}>
                  <label className="form-label" htmlFor={`reasignar-${c.id}`}>Reasignar a</label>
                  <select
                    id={`reasignar-${c.id}`}
                    className="form-input"
                    value={nuevoAsignadoId}
                    onChange={(e) => setNuevoAsignadoId(e.target.value)}
                  >
                    <option value="">Selecciona una persona</option>
                    {candidatos.map((u) => (
                      <option key={u.id} value={u.id}>{u.nombre}</option>
                    ))}
                  </select>
                  <div className="form-row" style={{ marginTop: 10 }}>
                    <button
                      className="btn-primary"
                      disabled={!nuevoAsignadoId || enviando}
                      onClick={() => handleReasignar(c.idea_id)}
                    >
                      {enviando ? 'Reasignando...' : 'Proponer reasignación'}
                    </button>
                    <button className="btn-secundario" onClick={cerrarAccion}>Cancelar</button>
                  </div>
                </div>
              ) : (
                <div className="persona-card-actions" style={{ marginTop: 12 }}>
                  <button className="btn-small exito" onClick={() => handleAprobar(c.idea_id)}>
                    Aprobar
                  </button>
                  <button
                    className="btn-small peligro"
                    onClick={() => setAccionAbierta({ comiteId: c.id, tipo: 'motivo-rechazo' })}
                  >
                    Rechazar
                  </button>
                  <button
                    className="btn-small"
                    onClick={() => abrirReasignar(c.id, c.idea_id)}
                  >
                    Reasignar
                  </button>
                  <button className="btn-small" onClick={() => setRiceAbiertoPara(c.idea_id)}>
                    Llenar RICE
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {riceAbiertoPara !== null && (
        <FormularioRice ideaId={riceAbiertoPara} onCerrar={() => setRiceAbiertoPara(null)} />
      )}
    </div>
  )
}

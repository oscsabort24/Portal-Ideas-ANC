import { useEffect, useState } from 'react'
import { FiFileText } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import DocumentosGenerados from '../../documentos/components/DocumentosGenerados'
import ResumenYPreguntas from '../../ideas/components/ResumenYPreguntas'
import { listarUsuarios } from '../../usuarios/api'
import { useEsMiembroCab } from '../../usuarios/hooks/useEsMiembroCab'
import type { TipoCAB, Usuario } from '../../usuarios/types'
import { aprobar, colaComite, rechazar } from '../api'
import FormularioRice from './FormularioRice'
import type { ComiteIdeaDetalle } from '../types'

const ETIQUETA_TIPO_CAB: Record<TipoCAB, string> = {
  innovacion: 'CAB Innovación',
  transformacion_digital: 'CAB Transformación Digital',
}

const TODOS_LOS_TIPOS: TipoCAB[] = ['innovacion', 'transformacion_digital']

export default function ColaComite() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const { tiposCab: misTiposCab, cargando: cargandoMembresias, error: errorMembresias } = useEsMiembroCab()
  const [tipoSeleccionado, setTipoSeleccionado] = useState<TipoCAB | null>(null)
  const [cola, setCola] = useState<ComiteIdeaDetalle[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [cargandoCola, setCargandoCola] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [motivoAbiertoPara, setMotivoAbiertoPara] = useState<number | null>(null)
  const [motivo, setMotivo] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [riceAbiertoPara, setRiceAbiertoPara] = useState<number | null>(null)

  useEffect(() => {
    listarUsuarios()
      .then(setUsuarios)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los usuarios'))
  }, [])

  useEffect(() => {
    if (misTiposCab === null || tipoSeleccionado) return
    const disponibles = esAdmin ? TODOS_LOS_TIPOS : misTiposCab
    if (disponibles.length > 0) setTipoSeleccionado(disponibles[0])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [misTiposCab, esAdmin])

  function cargarCola(tipo: TipoCAB) {
    setCargandoCola(true)
    setError(null)
    colaComite(tipo)
      .then(setCola)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la cola del comité'))
      .finally(() => setCargandoCola(false))
  }

  useEffect(() => {
    if (tipoSeleccionado) cargarCola(tipoSeleccionado)
  }, [tipoSeleccionado])

  function nombreAutor(autorId: number): string {
    return usuarios.find((u) => u.id === autorId)?.nombre ?? '—'
  }

  function cerrarMotivo() {
    setMotivoAbiertoPara(null)
    setMotivo('')
  }

  async function handleAprobar(ideaId: number) {
    const confirmado = window.confirm('¿Aprobar esta idea?')
    if (!confirmado) return
    setError(null)
    try {
      await aprobar(ideaId)
      // Los documentos ya no se generan acá: para cuando una idea llega a
      // esta cola, ComiteIdea ya existe y los documentos quedaron
      // congelados (ver documentos/router.py:_puede_generar) — el autor ya
      // los generó (o no) antes de que la idea llegara a comité. Aprobar
      // vuelve a ser una acción simple.
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
      cerrarMotivo()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo rechazar la idea')
    } finally {
      setEnviando(false)
    }
  }

  if (cargandoMembresias || misTiposCab === null) return <p>Cargando...</p>

  const disponibles = esAdmin ? TODOS_LOS_TIPOS : misTiposCab

  if (disponibles.length === 0) {
    return (
      <div>
        <h1 className="page-title">Cola del comité</h1>
        <p className="cab-vacio">No eres miembro de ningún CAB.</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="page-title">Cola del comité</h1>

      {(error || errorMembresias) && <p className="form-error">{error || errorMembresias}</p>}

      {disponibles.length > 1 && (
        <div className="tabs-row">
          {disponibles.map((tipo) => (
            <button
              key={tipo}
              className={`tab-button ${tipoSeleccionado === tipo ? 'active' : ''}`}
              onClick={() => setTipoSeleccionado(tipo)}
            >
              {ETIQUETA_TIPO_CAB[tipo]}
            </button>
          ))}
        </div>
      )}

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
                    <div className="idea-card-title">#{indice + 1} — {c.idea.titulo}</div>
                    <div className="idea-card-date">
                      De {nombreAutor(c.idea.autor_id)} — en cola desde{' '}
                      {new Date(c.creado_en).toLocaleDateString('es-CR')}
                    </div>
                  </div>
                </div>
              </div>

              <ResumenYPreguntas ideaId={c.idea_id} origen="comite" />

              {/* Solo lectura para CAB: los documentos ya quedaron
                  congelados apenas la idea llegó a esta cola (existe
                  ComiteIdea). puede_generar viene en false desde el
                  backend, así que este mismo componente no ofrece
                  generar/regenerar acá — se auto-oculta si el autor no
                  generó nada. */}
              <DocumentosGenerados ideaId={c.idea_id} />

              {motivoAbiertoPara === c.id ? (
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
                    <button className="btn-secundario" onClick={cerrarMotivo}>Cancelar</button>
                  </div>
                </div>
              ) : (
                <div className="persona-card-actions" style={{ marginTop: 12 }}>
                  <button className="btn-small exito" onClick={() => handleAprobar(c.idea_id)}>
                    Aprobar
                  </button>
                  <button className="btn-small peligro" onClick={() => setMotivoAbiertoPara(c.id)}>
                    Rechazar
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

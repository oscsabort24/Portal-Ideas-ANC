import { useEffect, useState } from 'react'
import { FiAlertTriangle, FiDownload, FiEye, FiFileText, FiRefreshCw } from 'react-icons/fi'
import { descargarDocumento, descargarZip, generarDocumentos, listarDocumentos, obtenerPendientes } from '../api'
import { ETIQUETA_TIPO_DOCUMENTO, ORDEN_TIPOS_DOCUMENTO, type DocumentoGenerado, type TipoDocumento } from '../types'
import SelectorGenerarDocumentos from './SelectorGenerarDocumentos'
import VistaPreviaDocumento from './VistaPreviaDocumento'

export default function DocumentosGenerados({ ideaId }: { ideaId: number }) {
  const [documentos, setDocumentos] = useState<DocumentoGenerado[]>([])
  const [pendientes, setPendientes] = useState<TipoDocumento[]>([])
  const [tiposPermitidosRol, setTiposPermitidosRol] = useState<TipoDocumento[]>([])
  const [puedeGenerar, setPuedeGenerar] = useState(false)
  const [documentosDesactualizados, setDocumentosDesactualizados] = useState(false)
  const [cargando, setCargando] = useState(true)
  const [seleccionados, setSeleccionados] = useState<Set<TipoDocumento>>(new Set())
  const [descargandoZip, setDescargandoZip] = useState(false)
  const [descargandoTipo, setDescargandoTipo] = useState<TipoDocumento | null>(null)
  const [regenerandoTipo, setRegenerandoTipo] = useState<TipoDocumento | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [previaAbierta, setPreviaAbierta] = useState<TipoDocumento | null>(null)

  function cargar(marcarCargando: boolean) {
    if (marcarCargando) setCargando(true)
    return Promise.all([listarDocumentos(ideaId).catch(() => []), obtenerPendientes(ideaId).catch(() => null)])
      .then(([docs, info]) => {
        setDocumentos(docs)
        setPendientes(info?.pendientes ?? [])
        setTiposPermitidosRol(info?.tipos_permitidos_rol ?? [])
        setPuedeGenerar(info?.puede_generar ?? false)
        setDocumentosDesactualizados(info?.documentos_desactualizados ?? false)
      })
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    cargar(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ideaId])

  // Nada que mostrar todavía: ni documentos generados ni pendientes por
  // ofrecer (ej. la idea todavía no tiene nada generado y tampoco se puede
  // generar — no aplica para quien la está viendo).
  if (cargando || (documentos.length === 0 && pendientes.length === 0)) return null

  const documentosOrdenados = ORDEN_TIPOS_DOCUMENTO.map((tipo) => documentos.find((d) => d.tipo_documento === tipo)).filter(
    (d): d is DocumentoGenerado => d !== undefined,
  )

  // Mismo filtro que ya aplica el backend en _tipos_permitidos_para_rol —
  // sin esto, un colaborador (solo "onepager" habilitado) veía checkboxes
  // para charter/bpmn/raci/bmc/business_case que el POST /generar de
  // todas formas iba a rechazar con 403.
  const pendientesPermitidos = pendientes.filter((tipo) => tiposPermitidosRol.includes(tipo))

  function toggleSeleccionado(tipo: TipoDocumento) {
    setSeleccionados((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(tipo)) siguiente.delete(tipo)
      else siguiente.add(tipo)
      return siguiente
    })
  }

  async function handleDescargarIndividual(tipo: TipoDocumento) {
    setDescargandoTipo(tipo)
    setError(null)
    try {
      await descargarDocumento(ideaId, tipo)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo descargar el documento')
    } finally {
      setDescargandoTipo(null)
    }
  }

  async function handleRegenerar(tipo: TipoDocumento) {
    const confirmado = window.confirm('¿Regenerar este documento? Se perderá el contenido actual.')
    if (!confirmado) return
    setRegenerandoTipo(tipo)
    setError(null)
    try {
      await generarDocumentos(ideaId, [tipo])
      await cargar(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo regenerar el documento')
    } finally {
      setRegenerandoTipo(null)
    }
  }

  async function handleDescargarZip() {
    if (seleccionados.size === 0) return
    setDescargandoZip(true)
    setError(null)
    try {
      await descargarZip(ideaId, Array.from(seleccionados))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo descargar el ZIP')
    } finally {
      setDescargandoZip(false)
    }
  }

  return (
    <div style={{ padding: '20px', borderTop: '1px solid var(--border-light)' }}>
      <h2 className="page-title" style={{ fontSize: 18, marginBottom: 12 }}>
        Documentos generados
      </h2>

      {documentosDesactualizados && (
        <div className="banner-documentos-desactualizados">
          <FiAlertTriangle style={{ marginRight: 6, flexShrink: 0 }} />
          Estos documentos podrían estar desactualizados — la idea tuvo cambios solicitados después de la última generación.
        </div>
      )}

      {error && <p className="form-error">{error}</p>}

      {documentosOrdenados.length > 0 && (
        <>
          <div className="tabla-personas">
            {documentosOrdenados.map((doc) => (
              <div key={doc.id} className="idea-card idea-card-enviada">
                <div className="idea-card-header">
                  <div className="idea-card-title-row">
                    <input
                      type="checkbox"
                      checked={seleccionados.has(doc.tipo_documento)}
                      onChange={() => toggleSeleccionado(doc.tipo_documento)}
                      aria-label={`Seleccionar ${ETIQUETA_TIPO_DOCUMENTO[doc.tipo_documento]}`}
                    />
                    <FiFileText className="idea-card-icon idea-card-icon-enviada" />
                    <div>
                      <div className="idea-card-title">{ETIQUETA_TIPO_DOCUMENTO[doc.tipo_documento]}</div>
                      <div className="idea-card-date">
                        Generado el {new Date(doc.generado_en).toLocaleDateString('es-CR')}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="persona-card-actions" style={{ marginTop: 12 }}>
                  <button className="btn-small" onClick={() => setPreviaAbierta(doc.tipo_documento)}>
                    <FiEye style={{ marginRight: 4 }} />
                    Vista previa
                  </button>
                  <button
                    className="btn-small"
                    disabled={descargandoTipo === doc.tipo_documento}
                    onClick={() => handleDescargarIndividual(doc.tipo_documento)}
                  >
                    <FiDownload style={{ marginRight: 4 }} />
                    Descargar
                  </button>
                  {puedeGenerar && tiposPermitidosRol.includes(doc.tipo_documento) && (
                    <button
                      className="btn-small"
                      disabled={regenerandoTipo === doc.tipo_documento}
                      onClick={() => handleRegenerar(doc.tipo_documento)}
                    >
                      <FiRefreshCw style={{ marginRight: 4 }} />
                      {regenerandoTipo === doc.tipo_documento ? 'Regenerando...' : 'Regenerar'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16 }}>
            <button className="btn-small exito" disabled={seleccionados.size === 0 || descargandoZip} onClick={handleDescargarZip}>
              <FiDownload style={{ marginRight: 4 }} />
              Descargar seleccionados (ZIP)
            </button>
          </div>
        </>
      )}

      {puedeGenerar && pendientesPermitidos.length > 0 && (
        <SelectorGenerarDocumentos ideaId={ideaId} tiposPendientes={pendientesPermitidos} onGenerado={() => cargar(false)} />
      )}

      {previaAbierta && (
        <VistaPreviaDocumento ideaId={ideaId} tipo={previaAbierta} onCerrar={() => setPreviaAbierta(null)} />
      )}
    </div>
  )
}

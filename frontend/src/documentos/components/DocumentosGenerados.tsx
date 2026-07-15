import { useEffect, useState } from 'react'
import { FiDownload, FiFileText } from 'react-icons/fi'
import { descargarDocumento, descargarZip, listarDocumentos } from '../api'
import { ETIQUETA_TIPO_DOCUMENTO, ORDEN_TIPOS_DOCUMENTO, type DocumentoGenerado, type TipoDocumento } from '../types'

export default function DocumentosGenerados({ ideaId }: { ideaId: number }) {
  const [documentos, setDocumentos] = useState<DocumentoGenerado[]>([])
  const [cargando, setCargando] = useState(true)
  const [seleccionados, setSeleccionados] = useState<Set<TipoDocumento>>(new Set())
  const [descargandoZip, setDescargandoZip] = useState(false)
  const [descargandoTipo, setDescargandoTipo] = useState<TipoDocumento | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    listarDocumentos(ideaId)
      .then((docs) => {
        if (!cancelado) setDocumentos(docs)
      })
      .catch(() => {
        // 404 (todavía no hay documentos) u otro fallo al cargar: la sección
        // simplemente no aparece — no es un error que el usuario deba ver.
        if (!cancelado) setDocumentos([])
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [ideaId])

  if (cargando || documentos.length === 0) return null

  const documentosOrdenados = ORDEN_TIPOS_DOCUMENTO.map((tipo) => documentos.find((d) => d.tipo_documento === tipo)).filter(
    (d): d is DocumentoGenerado => d !== undefined,
  )

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

      {error && <p className="form-error">{error}</p>}

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
              <button
                className="btn-small"
                disabled={descargandoTipo === doc.tipo_documento}
                onClick={() => handleDescargarIndividual(doc.tipo_documento)}
              >
                <FiDownload style={{ marginRight: 4 }} />
                Descargar
              </button>
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
    </div>
  )
}

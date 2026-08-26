import { useEffect, useState } from 'react'
import { FiDownload, FiX } from 'react-icons/fi'
import { descargarDocumento, descargarPdf, obtenerPreviewHtml } from '../api'
import { ETIQUETA_TIPO_DOCUMENTO, type TipoDocumento } from '../types'

export default function VistaPreviaDocumento({
  ideaId,
  tipo,
  onCerrar,
}: {
  ideaId: number
  tipo: TipoDocumento
  onCerrar: () => void
}) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [descargandoWord, setDescargandoWord] = useState(false)
  const [descargandoPdf, setDescargandoPdf] = useState(false)

  useEffect(() => {
    let cancelado = false
    obtenerPreviewHtml(ideaId, tipo)
      .then((contenido) => {
        if (!cancelado) setHtml(contenido)
      })
      .catch((err) => {
        if (!cancelado) setError(err instanceof Error ? err.message : 'No se pudo cargar la vista previa')
      })
    return () => {
      cancelado = true
    }
  }, [ideaId, tipo])

  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === 'Escape') onCerrar()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onCerrar])

  async function handleDescargarWord() {
    setDescargandoWord(true)
    setError(null)
    try {
      await descargarDocumento(ideaId, tipo)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo descargar el Word')
    } finally {
      setDescargandoWord(false)
    }
  }

  async function handleDescargarPdf() {
    setDescargandoPdf(true)
    setError(null)
    try {
      await descargarPdf(ideaId, tipo)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo descargar el PDF')
    } finally {
      setDescargandoPdf(false)
    }
  }

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCerrar()
  }

  return (
    <div className="preview-overlay" onClick={handleOverlayClick} role="dialog" aria-modal="true">
      <div className="preview-modal">
        <div className="preview-modal-header">
          <span className="preview-modal-title">Vista previa — {ETIQUETA_TIPO_DOCUMENTO[tipo]}</span>
          <button className="preview-modal-close" onClick={onCerrar} aria-label="Cerrar vista previa">
            <FiX />
          </button>
        </div>

        <div className="preview-modal-body">
          {error && !html && (
            <div style={{ padding: 20 }}>
              <p className="form-error">{error}</p>
            </div>
          )}
          {!html && !error && (
            <div style={{ padding: 20 }}>
              <p>Cargando vista previa...</p>
            </div>
          )}
          {/* sandbox="": un <iframe srcDoc> SIN sandbox hereda el origen de la
              app, así que un <script> que se colara en el HTML del documento
              correría con acceso al DOM y al localStorage donde MSAL guarda
              los tokens. Con sandbox="" (lista de permisos vacía) el iframe
              va a un origen opaco y no ejecuta scripts. El documento es
              HTML+CSS puro —sin <script>, sin enlaces, sin formularios— así
              que no pierde nada. Es defensa en profundidad: el escape ya se
              hace al renderizar (documentos/plantillas_html.py). */}
          {html && (
            <iframe
              className="preview-modal-iframe"
              srcDoc={html}
              sandbox=""
              title={`Vista previa ${tipo}`}
            />
          )}
        </div>

        <div className="preview-modal-footer">
          {error && html && <span className="preview-modal-estado form-error">{error}</span>}
          <button className="btn-secundario" disabled={descargandoWord} onClick={handleDescargarWord}>
            <FiDownload style={{ marginRight: 4 }} />
            {descargandoWord ? 'Descargando...' : 'Descargar Word'}
          </button>
          <button className="btn-primary" disabled={descargandoPdf} onClick={handleDescargarPdf}>
            <FiDownload style={{ marginRight: 4 }} />
            {descargandoPdf ? 'Descargando...' : 'Descargar PDF'}
          </button>
        </div>
      </div>
    </div>
  )
}

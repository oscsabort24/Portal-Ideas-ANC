import { FiDownload, FiFileText } from 'react-icons/fi'
import { urlDescarga } from '../api'
import type { DocumentoCriterio, TipoCriterio } from '../types'

export default function DocumentoActivo({
  tipo,
  documento,
}: {
  tipo: TipoCriterio
  documento: DocumentoCriterio | null
}) {
  if (!documento) {
    return (
      <div className="item-simple">
        <FiFileText className="item-simple-icon" />
        Todavía no se ha subido ningún documento para este tipo.
      </div>
    )
  }

  const fecha = new Date(documento.subido_en).toLocaleString('es-CR', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

  return (
    <div className="documento-activo-card">
      <div className="persona-card-icon">
        <FiFileText />
      </div>
      <div className="documento-activo-info">
        <div className="persona-card-nombre">{documento.nombre_archivo}</div>
        <div className="persona-card-correo">Versión {documento.version}</div>
      </div>
      <div className="persona-card-meta">
        <span className="persona-meta-label">Subido por</span>
        <span>{documento.subido_por.nombre}</span>
      </div>
      <div className="persona-card-meta">
        <span className="persona-meta-label">Fecha</span>
        <span>{fecha}</span>
      </div>
      <div className="persona-card-actions">
        <a className="btn-small" href={urlDescarga(tipo)} target="_blank" rel="noreferrer">
          <FiDownload /> Descargar
        </a>
      </div>
    </div>
  )
}

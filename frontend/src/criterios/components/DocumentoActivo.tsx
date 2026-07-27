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
  const fechaEdicion = documento.actualizado_en
    ? new Date(documento.actualizado_en).toLocaleString('es-CR', { dateStyle: 'medium', timeStyle: 'short' })
    : null

  return (
    <div>
      <div className="documento-activo-card">
        <div className="persona-card-icon">
          <FiFileText />
        </div>
        <div className="documento-activo-info">
          <div className="persona-card-nombre">{documento.nombre_archivo}</div>
          <div className="persona-card-correo">Versión {documento.version}</div>
        </div>
        <div className="persona-card-meta">
          <span className="persona-meta-label">Archivo subido por</span>
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

      {fechaEdicion && (
        <p className="form-help">
          Última edición de texto: {fechaEdicion} por {documento.actualizado_por?.nombre}
        </p>
      )}

      <p className="form-help">
        {documento.descripcion || 'Sin descripción de para qué sirve este criterio todavía.'}
      </p>
    </div>
  )
}

import { useState } from 'react'
import { generarDocumentos } from '../api'
import { ETIQUETA_TIPO_DOCUMENTO, ORDEN_TIPOS_DOCUMENTO, type TipoDocumento } from '../types'

/**
 * Selector de checkboxes para disparar la generación manual de
 * documentos — usado tanto justo después de aprobar en ColaComite.tsx
 * como para completar pendientes en DocumentosGenerados.tsx.
 */
export default function SelectorGenerarDocumentos({
  ideaId,
  tiposPendientes,
  onGenerado,
  mostrarOmitir = false,
  onOmitir,
}: {
  ideaId: number
  tiposPendientes: TipoDocumento[]
  onGenerado: () => void
  mostrarOmitir?: boolean
  onOmitir?: () => void
}) {
  const [seleccionados, setSeleccionados] = useState<Set<TipoDocumento>>(new Set(tiposPendientes))
  const [generando, setGenerando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ordenados = ORDEN_TIPOS_DOCUMENTO.filter((tipo) => tiposPendientes.includes(tipo))

  function toggle(tipo: TipoDocumento) {
    setSeleccionados((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(tipo)) siguiente.delete(tipo)
      else siguiente.add(tipo)
      return siguiente
    })
  }

  async function handleGenerar() {
    if (seleccionados.size === 0) return
    setGenerando(true)
    setError(null)
    try {
      await generarDocumentos(ideaId, Array.from(seleccionados))
      onGenerado()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron generar los documentos')
    } finally {
      setGenerando(false)
    }
  }

  return (
    <div className="form-card" style={{ marginTop: 12 }}>
      <p className="form-label">Seleccioná los documentos a generar</p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        {ordenados.map((tipo) => (
          <label key={tipo} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13.5 }}>
            <input type="checkbox" checked={seleccionados.has(tipo)} onChange={() => toggle(tipo)} />
            {ETIQUETA_TIPO_DOCUMENTO[tipo]}
          </label>
        ))}
      </div>

      {error && <p className="form-error">{error}</p>}

      <div className="form-row">
        <button className="btn-primary" disabled={seleccionados.size === 0 || generando} onClick={handleGenerar}>
          {generando ? 'Generando...' : 'Generar ahora'}
        </button>
        {mostrarOmitir && (
          <button className="btn-secundario" disabled={generando} onClick={onOmitir}>
            Más tarde
          </button>
        )}
      </div>
    </div>
  )
}

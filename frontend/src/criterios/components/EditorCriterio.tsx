import { useEffect, useState, type FormEvent } from 'react'
import { editarDocumento } from '../api'
import type { DocumentoCriterio } from '../types'

export default function EditorCriterio({
  documento,
  onGuardado,
}: {
  documento: DocumentoCriterio
  onGuardado: (actualizado: DocumentoCriterio) => void
}) {
  const [descripcion, setDescripcion] = useState(documento.descripcion ?? '')
  const [contenido, setContenido] = useState(documento.contenido ?? '')
  const [pin, setPin] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exito, setExito] = useState(false)

  // Si el admin sube una versión nueva o cambia de tab, el formulario se
  // resetea al contenido/descripción de ESE documento (no arrastra lo que
  // se estaba editando del anterior).
  useEffect(() => {
    setDescripcion(documento.descripcion ?? '')
    setContenido(documento.contenido ?? '')
    setError(null)
    setExito(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documento.id])

  const huboCambios = descripcion !== (documento.descripcion ?? '') || contenido !== (documento.contenido ?? '')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!pin.trim() || !huboCambios) return

    setEnviando(true)
    setError(null)
    setExito(false)
    try {
      const actualizado = await editarDocumento(documento.id, {
        descripcion: descripcion.trim(),
        contenido,
        pin: pin.trim(),
      })
      onGuardado(actualizado)
      setPin('')
      setExito(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el criterio')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-field">
        <label className="form-label" htmlFor="criterio-descripcion">Para qué sirve este criterio</label>
        <input
          id="criterio-descripcion"
          type="text"
          className="form-input"
          value={descripcion}
          onChange={(e) => setDescripcion(e.target.value)}
          placeholder="Ej: define si una idea es de Innovación o de Transformación Digital"
          maxLength={500}
        />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="criterio-contenido">Contenido</label>
        <textarea
          id="criterio-contenido"
          className="form-input criterio-textarea"
          value={contenido}
          onChange={(e) => setContenido(e.target.value)}
          placeholder="Pega o escribe aquí el texto del criterio (si el documento activo es un .pdf, no se extrajo automáticamente — pegalo a mano una sola vez)."
          rows={14}
        />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="criterio-pin">Tu PIN (para confirmar el cambio)</label>
        <input
          id="criterio-pin"
          type="password"
          inputMode="numeric"
          className="form-input"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="••••"
        />
      </div>

      {error && <p className="form-error">{error}</p>}
      {exito && !error && <p className="nota-temporal">Cambios guardados.</p>}

      <button type="submit" className="btn-primary" disabled={!huboCambios || !pin.trim() || enviando}>
        {enviando ? 'Guardando...' : 'Guardar cambios'}
      </button>
    </form>
  )
}

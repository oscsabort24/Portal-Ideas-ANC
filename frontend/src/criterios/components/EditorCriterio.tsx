import { useEffect, useState, type FormEvent } from 'react'
import { guardarCriterio } from '../api'
import type { CriterioIA, TipoCriterio } from '../types'

export default function EditorCriterio({
  tipo,
  departamentoId,
  criterio,
  onGuardado,
}: {
  tipo: TipoCriterio
  departamentoId?: number
  criterio: CriterioIA | null
  onGuardado: (nuevo: CriterioIA) => void
}) {
  const [descripcion, setDescripcion] = useState(criterio?.descripcion ?? '')
  const [contenido, setContenido] = useState(criterio?.contenido ?? '')
  const [pin, setPin] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exito, setExito] = useState(false)

  // Al cambiar de pestaña/departamento, el formulario se resetea al
  // contenido de ESE criterio (no arrastra lo que se estaba editando).
  useEffect(() => {
    setDescripcion(criterio?.descripcion ?? '')
    setContenido(criterio?.contenido ?? '')
    setError(null)
    setExito(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipo, departamentoId, criterio?.id])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!pin.trim() || !contenido.trim()) return

    setEnviando(true)
    setError(null)
    setExito(false)
    try {
      const nuevo = await guardarCriterio(tipo, {
        contenido,
        descripcion: descripcion.trim() || undefined,
        departamento_id: departamentoId ?? null,
        pin: pin.trim(),
      })
      onGuardado(nuevo)
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
          placeholder="Escribí aquí el texto del criterio."
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
      {exito && !error && <p className="nota-temporal">Guardado como versión nueva.</p>}

      <button type="submit" className="btn-primary" disabled={!contenido.trim() || !pin.trim() || enviando}>
        {enviando ? 'Guardando...' : 'Guardar como versión nueva'}
      </button>
    </form>
  )
}

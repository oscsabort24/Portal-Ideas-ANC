import { useRef, useState, type FormEvent } from 'react'
import { subirDocumento } from '../api'
import type { DocumentoCriterio, TipoCriterio } from '../types'

export default function FormularioSubirDocumento({
  tipo,
  onSubido,
}: {
  tipo: TipoCriterio
  onSubido: (documento: DocumentoCriterio) => void
}) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [pin, setPin] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputArchivoRef = useRef<HTMLInputElement>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!archivo || !pin.trim()) return

    setEnviando(true)
    setError(null)
    try {
      const documento = await subirDocumento(tipo, archivo, pin.trim())
      onSubido(documento)
      setArchivo(null)
      setPin('')
      if (inputArchivoRef.current) inputArchivoRef.current.value = ''
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo subir el documento')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-field">
        <label className="form-label" htmlFor="archivo-criterio">Nuevo documento (.docx o .pdf)</label>
        <input
          id="archivo-criterio"
          type="file"
          className="form-input"
          accept=".docx,.pdf"
          ref={inputArchivoRef}
          onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="pin-subida">Tu PIN</label>
        <input
          id="pin-subida"
          type="password"
          inputMode="numeric"
          className="form-input"
          value={pin}
          onChange={(e) => setPin(e.target.value)}
          placeholder="••••"
        />
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-primary" disabled={!archivo || !pin.trim() || enviando}>
        {enviando ? 'Subiendo...' : 'Subir nueva versión'}
      </button>
    </form>
  )
}

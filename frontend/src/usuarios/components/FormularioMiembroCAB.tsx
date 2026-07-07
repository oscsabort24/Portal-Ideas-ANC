import { useState, type FormEvent } from 'react'
import { agregarMiembroCab } from '../api'
import type { MiembroCABDetalle, TipoCAB, Usuario } from '../types'

export default function FormularioMiembroCAB({
  personas,
  onAgregado,
}: {
  personas: Usuario[]
  onAgregado: (miembro: MiembroCABDetalle) => void
}) {
  const [usuarioId, setUsuarioId] = useState('')
  const [tipoCab, setTipoCab] = useState<TipoCAB>('innovacion')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!usuarioId) return

    setEnviando(true)
    setError(null)
    try {
      const miembro = await agregarMiembroCab({ usuario_id: Number(usuarioId), tipo_cab: tipoCab })
      const usuario = personas.find((p) => p.id === Number(usuarioId))
      if (usuario) onAgregado({ ...miembro, usuario })
      setUsuarioId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo agregar al comité')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <p className="nota-temporal">
        Ser miembro de un CAB es independiente del rol de la persona en el organigrama.
      </p>

      <div className="form-row">
        <div className="form-field">
          <label className="form-label" htmlFor="usuarioCab">Persona</label>
          <select id="usuarioCab" className="form-input" value={usuarioId} onChange={(e) => setUsuarioId(e.target.value)}>
            <option value="">Selecciona una persona</option>
            {personas.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="tipoCab">Comité</label>
          <select id="tipoCab" className="form-input" value={tipoCab} onChange={(e) => setTipoCab(e.target.value as TipoCAB)}>
            <option value="innovacion">Innovación</option>
            <option value="transformacion_digital">Transformación Digital</option>
          </select>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-primary" disabled={!usuarioId || enviando}>
        {enviando ? 'Agregando...' : 'Agregar al comité'}
      </button>
    </form>
  )
}

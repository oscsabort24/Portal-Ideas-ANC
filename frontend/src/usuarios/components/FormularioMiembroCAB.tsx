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
      if (usuario) onAgregado({ ...miembro, usuario, departamentos: [] })
      setUsuarioId('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo agregar al Portfolio Owner')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <p className="nota-temporal">
        Ser Portfolio Owner es independiente del rol de la persona en el organigrama.
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

        {/* El backend exige tipo_cab (MiembroCABCreate, nullable=False), así que
            el formulario tiene que seguir enviándolo. Se muestra a la vista y
            etiquetado como lo que realmente es en vez de ocultarlo con un
            default fijo: eso dejaría un dato que nadie eligió y que igual
            aparece en la ficha de cada persona. */}
        <div className="form-field">
          <label className="form-label" htmlFor="tipoCab">Clasificación</label>
          <select id="tipoCab" className="form-input" value={tipoCab} onChange={(e) => setTipoCab(e.target.value as TipoCAB)}>
            <option value="innovacion">Innovación</option>
            <option value="transformacion_digital">Transformación Digital</option>
          </select>
          <p className="form-help">
            Dato histórico: no afecta qué ideas ve esta persona. El alcance se define asignando
            departamentos después de agregarla.
          </p>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-primary" disabled={!usuarioId || enviando}>
        {enviando ? 'Agregando...' : 'Agregar Portfolio Owner'}
      </button>
    </form>
  )
}

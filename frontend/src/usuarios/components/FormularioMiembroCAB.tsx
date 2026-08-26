import { useState, type FormEvent } from 'react'
import { agregarMiembroCab } from '../api'
import type { Departamento, MiembroCABDetalle, Usuario } from '../types'
import { SelectorDepartamentos } from './ListaMiembrosCAB'

export default function FormularioMiembroCAB({
  personas,
  departamentos,
  onAgregado,
}: {
  personas: Usuario[]
  departamentos: Departamento[]
  onAgregado: (miembro: MiembroCABDetalle) => void
}) {
  const [usuarioId, setUsuarioId] = useState('')
  const [seleccion, setSeleccion] = useState<number[]>([])
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function alternar(id: number) {
    setSeleccion((prev) => (prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!usuarioId) return

    setEnviando(true)
    setError(null)
    try {
      // tipo_cab ya no se manda: el backend le aplica un default de
      // compatibilidad (ver usuarios/schemas.py:MiembroCABCreate). El alcance
      // real viaja en departamento_ids, en este mismo POST.
      const miembro = await agregarMiembroCab({
        usuario_id: Number(usuarioId),
        departamento_ids: seleccion,
      })
      // El backend responde MiembroCABDetalleOut, con usuario y departamentos
      // ya resueltos — no hay que reconstruirlos acá.
      onAgregado(miembro)
      setUsuarioId('')
      setSeleccion([])
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
        <label className="form-label">Departamentos que va a decidir</label>
        <p className="form-help">
          {seleccion.length === 0
            ? 'Sin ningún departamento seleccionado, esta persona verá las ideas de TODOS los departamentos.'
            : `Verá solo las ideas de ${seleccion.length} departamento${seleccion.length === 1 ? '' : 's'}.`}
        </p>
        <SelectorDepartamentos departamentos={departamentos} seleccion={seleccion} onAlternar={alternar} />
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="btn-primary" disabled={!usuarioId || enviando}>
        {enviando ? 'Agregando...' : 'Agregar Portfolio Owner'}
      </button>
    </form>
  )
}

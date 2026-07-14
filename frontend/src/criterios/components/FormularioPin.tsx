import { useEffect, useState, type FormEvent } from 'react'
import { FiCheckCircle } from 'react-icons/fi'
import { definirPin } from '../api'

export default function FormularioPin({
  modo,
  onGuardado,
  onCancelar,
}: {
  modo: 'crear' | 'cambiar'
  onGuardado: () => void
  onCancelar?: () => void
}) {
  const [pinActual, setPinActual] = useState('')
  const [pinNuevo, setPinNuevo] = useState('')
  const [pinConfirmar, setPinConfirmar] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exito, setExito] = useState(false)

  useEffect(() => {
    if (!exito) return
    const temporizador = setTimeout(onGuardado, 1600)
    return () => clearTimeout(temporizador)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exito])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!pinNuevo.trim()) return

    if (pinNuevo.trim() !== pinConfirmar.trim()) {
      setError('Los PIN no coinciden')
      return
    }

    setEnviando(true)
    setError(null)
    try {
      await definirPin({
        pin_actual: modo === 'cambiar' ? pinActual.trim() : undefined,
        pin_nuevo: pinNuevo.trim(),
      })
      setExito(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar el PIN')
    } finally {
      setEnviando(false)
    }
  }

  if (exito) {
    return (
      <div className="banner-exito">
        <FiCheckCircle />
        {modo === 'crear' ? 'PIN creado correctamente.' : 'PIN actualizado correctamente.'}
      </div>
    )
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <p className="nota-temporal">
        {modo === 'crear'
          ? 'Define tu PIN personal (4 a 6 dígitos). Lo necesitarás para subir nuevas versiones de los documentos de criterios.'
          : 'Confirma tu PIN actual y define uno nuevo.'}
      </p>

      {modo === 'cambiar' && (
        <div className="form-field">
          <label className="form-label" htmlFor="pin-actual">PIN actual</label>
          <input
            id="pin-actual"
            type="password"
            inputMode="numeric"
            className="form-input"
            value={pinActual}
            onChange={(e) => setPinActual(e.target.value)}
            placeholder="••••"
          />
        </div>
      )}

      <div className="form-row">
        <div className="form-field">
          <label className="form-label" htmlFor="pin-nuevo">PIN nuevo</label>
          <input
            id="pin-nuevo"
            type="password"
            inputMode="numeric"
            className="form-input"
            value={pinNuevo}
            onChange={(e) => setPinNuevo(e.target.value)}
            placeholder="Entre 4 y 6 dígitos"
          />
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="pin-confirmar">Confirmar PIN nuevo</label>
          <input
            id="pin-confirmar"
            type="password"
            inputMode="numeric"
            className="form-input"
            value={pinConfirmar}
            onChange={(e) => setPinConfirmar(e.target.value)}
            placeholder="Repite el PIN nuevo"
          />
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      <div className="form-row">
        <button
          type="submit"
          className="btn-primary"
          disabled={
            !pinNuevo.trim() ||
            !pinConfirmar.trim() ||
            (modo === 'cambiar' && !pinActual.trim()) ||
            enviando
          }
        >
          {enviando ? 'Guardando...' : modo === 'crear' ? 'Crear PIN' : 'Guardar nuevo PIN'}
        </button>
        {modo === 'cambiar' && onCancelar && (
          <button type="button" className="btn-secundario" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}

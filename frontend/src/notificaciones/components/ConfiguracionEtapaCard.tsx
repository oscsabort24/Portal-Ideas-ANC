import { useState } from 'react'
import { FiClock } from 'react-icons/fi'
import type { Usuario } from '../../usuarios/types'
import { actualizarConfig } from '../api'
import { ETIQUETA_ETAPA, type ConfiguracionEscalamiento, type EtapaEscalamiento } from '../types'

export default function ConfiguracionEtapaCard({
  config,
  usuarios,
  onGuardado,
}: {
  config: ConfiguracionEscalamiento
  usuarios: Usuario[]
  onGuardado: (config: ConfiguracionEscalamiento) => void
}) {
  const [plazoDias, setPlazoDias] = useState<string>(config.plazo_dias === null ? '' : String(config.plazo_dias))
  const [responsableId, setResponsableId] = useState<string>(
    config.responsable_id === null ? '' : String(config.responsable_id),
  )
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const activa = config.plazo_dias !== null

  async function handleGuardar() {
    setGuardando(true)
    setError(null)
    try {
      const actualizado = await actualizarConfig(config.etapa as EtapaEscalamiento, {
        plazo_dias: plazoDias.trim() === '' ? null : Number(plazoDias),
        responsable_id: responsableId.trim() === '' ? null : Number(responsableId),
      })
      onGuardado(actualizado)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la configuración')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="idea-card idea-card-enviada">
      <div className="idea-card-header">
        <div className="idea-card-title-row">
          <FiClock className="idea-card-icon idea-card-icon-enviada" />
          <div>
            <div className="idea-card-title">{ETIQUETA_ETAPA[config.etapa]}</div>
            <div className="idea-card-date">
              <span style={{ color: activa ? 'var(--success)' : 'var(--text-light)', fontWeight: 600 }}>
                {activa ? 'Activa' : 'Inactiva'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      <div style={{ marginTop: 12 }}>
        <label className="form-label" htmlFor={`plazo-${config.etapa}`}>
          Plazo (días)
        </label>
        <input
          id={`plazo-${config.etapa}`}
          className="form-input"
          type="number"
          min={0}
          placeholder="Vacío = inactiva"
          value={plazoDias}
          onChange={(e) => setPlazoDias(e.target.value)}
        />
      </div>

      <div style={{ marginTop: 12 }}>
        <label className="form-label" htmlFor={`responsable-${config.etapa}`}>
          Responsable
        </label>
        <select
          id={`responsable-${config.etapa}`}
          className="form-input"
          value={responsableId}
          onChange={(e) => setResponsableId(e.target.value)}
        >
          <option value="">Sin responsable</option>
          {usuarios.map((u) => (
            <option key={u.id} value={u.id}>
              {u.nombre}
            </option>
          ))}
        </select>
      </div>

      <div className="persona-card-actions" style={{ marginTop: 16 }}>
        <button className="btn-primary" disabled={guardando} onClick={handleGuardar}>
          Guardar
        </button>
      </div>
    </div>
  )
}

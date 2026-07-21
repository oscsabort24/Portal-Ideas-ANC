import { useEffect, useState } from 'react'
import { FiX } from 'react-icons/fi'
import { guardarRice, obtenerRice } from '../api'
import {
  ETIQUETA_ESFUERZO,
  ETIQUETA_IMPACTO_CONFIANZA,
  ETIQUETA_PRESUPUESTO,
  ETIQUETA_PRIORIDAD_RICE,
  type NivelEsfuerzo,
  type NivelImpactoConfianza,
  type PresupuestoRango,
  type RiceEvaluacion,
  type RiceEvaluacionRequest,
} from '../types'

const PRESUPUESTOS: PresupuestoRango[] = ['0', '1-10000', '10001-20000', '20001-30000', '+30000']
const NIVELES_IMPACTO_CONFIANZA: NivelImpactoConfianza[] = ['muy_bajo', 'medio', 'alto', 'muy_alto']
const NIVELES_ESFUERZO: NivelEsfuerzo[] = ['corto_plazo', 'medio_plazo', 'largo_plazo']

const COLOR_PRIORIDAD: Record<string, { bg: string; color: string }> = {
  baja: { bg: 'var(--success-bg)', color: 'var(--success)' },
  media: { bg: 'var(--partial-bg)', color: 'var(--partial)' },
  alta: { bg: 'var(--error-bg)', color: 'var(--error)' },
}

const VALOR_INICIAL: RiceEvaluacionRequest = {
  area: '',
  lider_funcional: '',
  paises: 1,
  presupuesto_rango: '0',
  impacta_plan_estrategico: false,
  alcance_departamentos: 1,
  impacto: 'medio',
  confianza: 'medio',
  esfuerzo: 'medio_plazo',
}

export default function FormularioRice({ ideaId, onCerrar }: { ideaId: number; onCerrar: () => void }) {
  const [valores, setValores] = useState<RiceEvaluacionRequest>(VALOR_INICIAL)
  const [resultado, setResultado] = useState<RiceEvaluacion | null>(null)
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelado = false
    obtenerRice(ideaId)
      .then((rice) => {
        if (cancelado) return
        setValores(rice)
        setResultado(rice)
      })
      .catch(() => {
        // Sin evaluación previa todavía — se llena desde cero, no es un error.
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })
    return () => {
      cancelado = true
    }
  }, [ideaId])

  function actualizarCampo<K extends keyof RiceEvaluacionRequest>(campo: K, valor: RiceEvaluacionRequest[K]) {
    setValores((prev) => ({ ...prev, [campo]: valor }))
  }

  async function handleGuardar() {
    if (!valores.area.trim() || !valores.lider_funcional.trim()) {
      setError('Área y líder funcional son obligatorios')
      return
    }
    setGuardando(true)
    setError(null)
    try {
      const rice = await guardarRice(ideaId, valores)
      setResultado(rice)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la evaluación RICE')
    } finally {
      setGuardando(false)
    }
  }

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target === e.currentTarget) onCerrar()
  }

  return (
    <div className="preview-overlay" onClick={handleOverlayClick} role="dialog" aria-modal="true">
      <div className="preview-modal" style={{ height: 'auto', maxHeight: '90vh' }}>
        <div className="preview-modal-header">
          <span className="preview-modal-title">Evaluación RICE</span>
          <button className="preview-modal-close" onClick={onCerrar} aria-label="Cerrar">
            <FiX />
          </button>
        </div>

        <div className="preview-modal-body" style={{ padding: 20, overflowY: 'auto' }}>
          {cargando ? (
            <p>Cargando...</p>
          ) : (
            <>
              <div className="form-row" style={{ flexWrap: 'wrap', gap: 12 }}>
                <div className="form-field" style={{ flex: 1, minWidth: 200 }}>
                  <label className="form-label">Área</label>
                  <input
                    type="text"
                    className="form-input"
                    value={valores.area}
                    onChange={(e) => actualizarCampo('area', e.target.value)}
                  />
                </div>
                <div className="form-field" style={{ flex: 1, minWidth: 200 }}>
                  <label className="form-label">Líder funcional</label>
                  <input
                    type="text"
                    className="form-input"
                    value={valores.lider_funcional}
                    onChange={(e) => actualizarCampo('lider_funcional', e.target.value)}
                  />
                </div>
              </div>

              <div className="form-row" style={{ flexWrap: 'wrap', gap: 12, marginTop: 12 }}>
                <div className="form-field" style={{ flex: 1, minWidth: 160 }}>
                  <label className="form-label">Países involucrados</label>
                  <input
                    type="number"
                    min={0}
                    className="form-input"
                    value={valores.paises}
                    onChange={(e) => actualizarCampo('paises', Number(e.target.value))}
                  />
                </div>
                <div className="form-field" style={{ flex: 1, minWidth: 160 }}>
                  <label className="form-label">Alcance (departamentos)</label>
                  <input
                    type="number"
                    min={0}
                    className="form-input"
                    value={valores.alcance_departamentos}
                    onChange={(e) => actualizarCampo('alcance_departamentos', Number(e.target.value))}
                  />
                </div>
                <div className="form-field" style={{ flex: 1, minWidth: 200 }}>
                  <label className="form-label">Presupuesto estimado</label>
                  <select
                    className="form-input"
                    value={valores.presupuesto_rango}
                    onChange={(e) => actualizarCampo('presupuesto_rango', e.target.value as PresupuestoRango)}
                  >
                    {PRESUPUESTOS.map((p) => (
                      <option key={p} value={p}>{ETIQUETA_PRESUPUESTO[p]}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row" style={{ flexWrap: 'wrap', gap: 12, marginTop: 12 }}>
                <div className="form-field" style={{ flex: 1, minWidth: 160 }}>
                  <label className="form-label">Impacto</label>
                  <select
                    className="form-input"
                    value={valores.impacto}
                    onChange={(e) => actualizarCampo('impacto', e.target.value as NivelImpactoConfianza)}
                  >
                    {NIVELES_IMPACTO_CONFIANZA.map((n) => (
                      <option key={n} value={n}>{ETIQUETA_IMPACTO_CONFIANZA[n]}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field" style={{ flex: 1, minWidth: 160 }}>
                  <label className="form-label">Confianza</label>
                  <select
                    className="form-input"
                    value={valores.confianza}
                    onChange={(e) => actualizarCampo('confianza', e.target.value as NivelImpactoConfianza)}
                  >
                    {NIVELES_IMPACTO_CONFIANZA.map((n) => (
                      <option key={n} value={n}>{ETIQUETA_IMPACTO_CONFIANZA[n]}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field" style={{ flex: 1, minWidth: 160 }}>
                  <label className="form-label">Esfuerzo</label>
                  <select
                    className="form-input"
                    value={valores.esfuerzo}
                    onChange={(e) => actualizarCampo('esfuerzo', e.target.value as NivelEsfuerzo)}
                  >
                    {NIVELES_ESFUERZO.map((n) => (
                      <option key={n} value={n}>{ETIQUETA_ESFUERZO[n]}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-field" style={{ marginTop: 12 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13.5 }}>
                  <input
                    type="checkbox"
                    checked={valores.impacta_plan_estrategico}
                    onChange={(e) => actualizarCampo('impacta_plan_estrategico', e.target.checked)}
                  />
                  Impacta el plan estratégico
                </label>
              </div>

              {error && <p className="form-error" style={{ marginTop: 12 }}>{error}</p>}

              {resultado && (
                <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                    Calificación: <strong>{resultado.calificacion.toFixed(2)}</strong>
                  </span>
                  <span
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      padding: '4px 12px',
                      borderRadius: 20,
                      background: COLOR_PRIORIDAD[resultado.prioridad].bg,
                      color: COLOR_PRIORIDAD[resultado.prioridad].color,
                    }}
                  >
                    Prioridad: {ETIQUETA_PRIORIDAD_RICE[resultado.prioridad]}
                  </span>
                </div>
              )}
            </>
          )}
        </div>

        <div className="preview-modal-footer">
          <button className="btn-secundario" onClick={onCerrar}>Cerrar</button>
          <button className="btn-primary" disabled={guardando || cargando} onClick={handleGuardar}>
            {guardando ? 'Guardando...' : 'Guardar evaluación'}
          </button>
        </div>
      </div>
    </div>
  )
}

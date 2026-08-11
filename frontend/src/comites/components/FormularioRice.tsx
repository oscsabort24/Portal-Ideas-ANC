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

// Mismos valores numéricos que comites/rice.py:calcular_calificacion — SOLO
// para mostrar de dónde sale la nota, el backend sigue siendo la única
// fuente de verdad del cálculo real (nunca se recalcula acá).
const VALOR_IMPACTO_CONFIANZA: Record<NivelImpactoConfianza, number> = {
  muy_bajo: 0.25,
  medio: 0.5,
  alto: 0.75,
  muy_alto: 1.0,
}

const VALOR_ESFUERZO: Record<NivelEsfuerzo, number> = {
  corto_plazo: 3,
  medio_plazo: 2,
  largo_plazo: 1,
}

const VALOR_PRESUPUESTO: Record<PresupuestoRango, number> = {
  '0': 0.1,
  '1-10000': 0.25,
  '10001-20000': 0.5,
  '20001-30000': 0.75,
  '+30000': 1.0,
}

// Espejo del override de negocio en comites/rice.py:calcular_calificacion —
// SOLO para saber si mostrar la etiqueta explicativa, el backend sigue
// siendo la única fuente de verdad de qué prioridad quedó guardada.
function esPrioridadPorOverride(rice: RiceEvaluacion): boolean {
  return rice.impacta_plan_estrategico && rice.prioridad === 'alta' && rice.calificacion <= 6.6
}

function DetalleCalculoRice({ rice }: { rice: RiceEvaluacion }) {
  const [abierto, setAbierto] = useState(false)
  const porOverride = esPrioridadPorOverride(rice)

  const valorImpacto = VALOR_IMPACTO_CONFIANZA[rice.impacto]
  const valorConfianza = VALOR_IMPACTO_CONFIANZA[rice.confianza]
  const valorEsfuerzo = VALOR_ESFUERZO[rice.esfuerzo]
  const valorPresupuesto = VALOR_PRESUPUESTO[rice.presupuesto_rango]

  const filas: { etiqueta: string; valorElegido: string; valorFormula: string }[] = [
    { etiqueta: 'Alcance (departamentos)', valorElegido: String(rice.alcance_departamentos), valorFormula: String(rice.alcance_departamentos) },
    { etiqueta: 'Impacto', valorElegido: ETIQUETA_IMPACTO_CONFIANZA[rice.impacto], valorFormula: valorImpacto.toFixed(2) },
    { etiqueta: 'Confianza', valorElegido: ETIQUETA_IMPACTO_CONFIANZA[rice.confianza], valorFormula: valorConfianza.toFixed(2) },
    { etiqueta: 'Esfuerzo', valorElegido: ETIQUETA_ESFUERZO[rice.esfuerzo], valorFormula: String(valorEsfuerzo) },
    { etiqueta: 'Países', valorElegido: String(rice.paises), valorFormula: String(rice.paises) },
    { etiqueta: 'Nivel de presupuesto', valorElegido: ETIQUETA_PRESUPUESTO[rice.presupuesto_rango], valorFormula: valorPresupuesto.toFixed(2) },
  ]

  return (
    <div style={{ marginTop: 12 }}>
      <button
        type="button"
        className="btn-secundario"
        style={{ fontSize: 12.5 }}
        onClick={() => setAbierto((prev) => !prev)}
      >
        {abierto ? 'Ocultar detalle del cálculo' : 'Ver detalle del cálculo'}
      </button>

      {abierto && (
        <div
          style={{
            marginTop: 10,
            border: '1px solid var(--border-light)',
            borderRadius: 'var(--radius)',
            padding: '12px 14px',
            background: 'var(--surface-2)',
          }}
        >
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '4px 8px 8px 0', fontWeight: 600 }}>Variable</th>
                <th style={{ padding: '4px 8px 8px 0', fontWeight: 600 }}>Valor asignado</th>
                <th style={{ padding: '4px 0 8px', fontWeight: 600 }}>Valor en la fórmula</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.etiqueta} style={{ borderTop: '1px solid var(--border-light)' }}>
                  <td style={{ padding: '6px 8px 6px 0' }}>{f.etiqueta}</td>
                  <td style={{ padding: '6px 8px 6px 0' }}>{f.valorElegido}</td>
                  <td style={{ padding: '6px 0', fontWeight: 600 }}>{f.valorFormula}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div
            style={{
              marginTop: 10,
              paddingTop: 10,
              borderTop: '1px solid var(--border-light)',
              fontSize: 12.5,
              color: 'var(--text-muted)',
              lineHeight: 1.6,
            }}
          >
            <div>Calificación = ((Alcance × Impacto × Confianza) / (Esfuerzo + Países)) × Nivel de Presupuesto</div>
            <div style={{ marginTop: 4 }}>
              = (({rice.alcance_departamentos} × {valorImpacto.toFixed(2)} × {valorConfianza.toFixed(2)}) / (
              {valorEsfuerzo} + {rice.paises})) × {valorPresupuesto.toFixed(2)}
            </div>
            <div style={{ marginTop: 4, color: 'var(--text)', fontWeight: 600 }}>
              = {rice.calificacion.toFixed(2)}
            </div>

            {porOverride && (
              <div
                style={{
                  marginTop: 10,
                  padding: '8px 10px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'var(--error-bg)',
                  color: 'var(--error)',
                  fontWeight: 600,
                }}
              >
                Prioridad Alta (por impacto en plan estratégico) — la Calificación numérica ({rice.calificacion.toFixed(2)})
                por sí sola daría una prioridad menor; la Prioridad quedó forzada a Alta porque la idea marca
                "Impacta el plan estratégico" (regla de negocio, no forma parte de la fórmula de la política ANCCR8.1P143-0).
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
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
                    {esPrioridadPorOverride(resultado) && ' (por impacto en plan estratégico)'}
                  </span>
                </div>
              )}

              {resultado && <DetalleCalculoRice rice={resultado} />}
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

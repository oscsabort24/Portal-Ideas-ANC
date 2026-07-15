import { useEffect, useState } from 'react'
import { FiBell } from 'react-icons/fi'
import { listarUsuarios } from '../../usuarios/api'
import type { Usuario } from '../../usuarios/types'
import { listarHistorial, obtenerConfig, revisarVencidas } from '../api'
import { ETIQUETA_ETAPA, ORDEN_ETAPAS, type ConfiguracionEscalamiento, type NotificacionEscalamiento } from '../types'
import ConfiguracionEtapaCard from './ConfiguracionEtapaCard'

export default function NotificacionesView() {
  const [configs, setConfigs] = useState<ConfiguracionEscalamiento[]>([])
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [historial, setHistorial] = useState<NotificacionEscalamiento[]>([])
  const [cargando, setCargando] = useState(true)
  const [revisando, setRevisando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      Promise.all(ORDEN_ETAPAS.map((etapa) => obtenerConfig(etapa))),
      listarUsuarios(),
      listarHistorial(),
    ])
      .then(([cfgs, usrs, hist]) => {
        setConfigs(cfgs)
        setUsuarios(usrs)
        setHistorial(hist)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la configuración'))
      .finally(() => setCargando(false))
  }, [])

  function handleConfigGuardada(actualizado: ConfiguracionEscalamiento) {
    setConfigs((prev) => prev.map((c) => (c.etapa === actualizado.etapa ? actualizado : c)))
  }

  async function handleRevisarVencidas() {
    const confirmado = window.confirm(
      '¿Revisar vencidas ahora? Esto generará notificaciones reales para toda idea pendiente que supere el plazo configurado.',
    )
    if (!confirmado) return

    setRevisando(true)
    setError(null)
    try {
      const resultado = await revisarVencidas()
      if (resultado.notificaciones_generadas > 0) {
        const actualizado = await listarHistorial()
        setHistorial(actualizado)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo ejecutar la revisión')
    } finally {
      setRevisando(false)
    }
  }

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <h1 className="page-title">Notificaciones</h1>

      {error && <p className="form-error">{error}</p>}

      <h2 style={{ fontSize: 16, fontWeight: 600, margin: '20px 0 12px' }}>Configuración por etapa</h2>
      <div className="tabla-personas" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
        {configs.map((config) => (
          <ConfiguracionEtapaCard key={config.etapa} config={config} usuarios={usuarios} onGuardado={handleConfigGuardada} />
        ))}
      </div>

      <h2 style={{ fontSize: 16, fontWeight: 600, margin: '28px 0 12px' }}>Historial de escalamientos</h2>
      <div className="persona-card-actions" style={{ marginBottom: 16 }}>
        <button className="btn-primary" disabled={revisando} onClick={handleRevisarVencidas}>
          <FiBell style={{ marginRight: 6 }} />
          Revisar vencidas ahora
        </button>
      </div>

      {historial.length === 0 ? (
        <p className="cab-vacio">No hay notificaciones de escalamiento generadas todavía.</p>
      ) : (
        <div className="tabla-personas">
          {historial.map((n) => (
            <div key={n.id} className="idea-card idea-card-enviada">
              <div className="idea-card-header">
                <div className="idea-card-title-row">
                  <FiBell className="idea-card-icon idea-card-icon-enviada" />
                  <div>
                    <div className="idea-card-title">
                      {n.idea.titulo} — {ETIQUETA_ETAPA[n.etapa]}
                    </div>
                    <div className="idea-card-date">
                      Responsable: {n.responsable?.nombre ?? '—'} · {n.dias_transcurridos} día(s) transcurridos ·{' '}
                      {new Date(n.generada_en).toLocaleString('es-CR')}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

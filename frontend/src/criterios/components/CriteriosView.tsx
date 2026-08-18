import { useEffect, useState } from 'react'
import { obtenerCoberturaEntrevista, obtenerCriterioActivo, obtenerEstadoPin, obtenerHistorial } from '../api'
import { ETIQUETA_TIPO_CRITERIO, type CoberturaDepartamento, type CriterioIA, type TipoCriterio } from '../types'
import EditorCriterio from './EditorCriterio'
import FormularioPin from './FormularioPin'
import HistorialVersiones from './HistorialVersiones'

const TIPOS: TipoCriterio[] = ['clasificacion', 'asignacion_revisor', 'entrevista']

function NoHayCriterioActivo(err: unknown): boolean {
  return err instanceof Error && err.message.includes('No hay un criterio activo')
}

function InfoCriterioActivo({ criterio }: { criterio: CriterioIA | null }) {
  if (!criterio) {
    return <p className="cab-vacio">Todavía no hay un criterio guardado para esto.</p>
  }
  const fecha = new Date(criterio.creado_en).toLocaleString('es-CR', { dateStyle: 'medium', timeStyle: 'short' })
  return (
    <div className="item-simple">
      <span>Versión {criterio.version} — creado por {criterio.creado_por.nombre} · {fecha}</span>
      {criterio.descripcion && <p className="form-help">{criterio.descripcion}</p>}
    </div>
  )
}

function SeccionCriterio({ tipo, departamentoId }: { tipo: TipoCriterio; departamentoId?: number }) {
  const [tienePin, setTienePin] = useState<boolean | null>(null)
  const [mostrarCambiarPin, setMostrarCambiarPin] = useState(false)
  const [criterio, setCriterio] = useState<CriterioIA | null>(null)
  const [historial, setHistorial] = useState<CriterioIA[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function cargarCriterios() {
    setCargando(true)
    setError(null)
    Promise.all([
      obtenerCriterioActivo(tipo, departamentoId).catch((err) => {
        if (NoHayCriterioActivo(err)) return null
        throw err
      }),
      obtenerHistorial(tipo, departamentoId),
    ])
      .then(([c, hist]) => {
        setCriterio(c)
        setHistorial(hist)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar el criterio'))
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    obtenerEstadoPin()
      .then((r) => setTienePin(r.tiene_pin))
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo consultar el estado del PIN'))
    cargarCriterios()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipo, departamentoId])

  function handleGuardado(nuevo: CriterioIA) {
    setCriterio(nuevo)
    cargarCriterios()
  }

  if (cargando || tienePin === null) return <p>Cargando...</p>

  return (
    <div>
      {error && <p className="form-error">{error}</p>}

      {!tienePin ? (
        <FormularioPin modo="crear" onGuardado={() => setTienePin(true)} />
      ) : mostrarCambiarPin ? (
        <FormularioPin
          modo="cambiar"
          onGuardado={() => setMostrarCambiarPin(false)}
          onCancelar={() => setMostrarCambiarPin(false)}
        />
      ) : (
        <div className="tab-actions-row">
          <p className="nota-temporal">Ya tienes un PIN personal definido.</p>
          <button className="btn-small" onClick={() => setMostrarCambiarPin(true)}>
            Cambiar PIN
          </button>
        </div>
      )}

      <h2 className="cab-grupo-titulo">Criterio activo</h2>
      <InfoCriterioActivo criterio={criterio} />

      {tienePin && (
        <>
          <h2 className="cab-grupo-titulo">Editar / guardar nueva versión</h2>
          <EditorCriterio tipo={tipo} departamentoId={departamentoId} criterio={criterio} onGuardado={handleGuardado} />
        </>
      )}

      <h2 className="cab-grupo-titulo">Historial de versiones</h2>
      <HistorialVersiones historial={historial} />
    </div>
  )
}

function SeccionEntrevista() {
  const [cobertura, setCobertura] = useState<CoberturaDepartamento[]>([])
  const [departamentoId, setDepartamentoId] = useState<number | undefined>(undefined)

  useEffect(() => {
    obtenerCoberturaEntrevista().then(setCobertura)
  }, [])

  return (
    <div>
      <div className="form-field">
        <label className="form-label" htmlFor="entrevista-departamento">Alcance</label>
        <select
          id="entrevista-departamento"
          className="form-input"
          value={departamentoId ?? ''}
          onChange={(e) => setDepartamentoId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">Default (aplica a los 18 departamentos salvo excepción)</option>
          {cobertura.map((d) => (
            <option key={d.departamento_id} value={d.departamento_id}>
              {d.nombre}
              {d.tiene_excepcion ? ' (tiene excepción propia)' : ''}
            </option>
          ))}
        </select>
        <p className="form-help">
          El texto que escribas acá se agrega AL FINAL de las reglas generales de la entrevista —
          nunca las reemplaza.
        </p>
      </div>

      <SeccionCriterio key={departamentoId ?? 'default'} tipo="entrevista" departamentoId={departamentoId} />
    </div>
  )
}

export default function CriteriosView() {
  const [tipoActivo, setTipoActivo] = useState<TipoCriterio>('clasificacion')

  return (
    <div>
      <h1 className="page-title">Criterios IA</h1>

      <div className="tabs-row">
        {TIPOS.map((tipo) => (
          <button
            key={tipo}
            className={`tab-button ${tipoActivo === tipo ? 'active' : ''}`}
            onClick={() => setTipoActivo(tipo)}
          >
            {ETIQUETA_TIPO_CRITERIO[tipo]}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {tipoActivo === 'entrevista' ? (
          <SeccionEntrevista />
        ) : (
          <SeccionCriterio key={tipoActivo} tipo={tipoActivo} />
        )}
      </div>
    </div>
  )
}

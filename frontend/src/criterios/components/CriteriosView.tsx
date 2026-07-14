import { useEffect, useState } from 'react'
import { obtenerDocumentoActivo, obtenerEstadoPin, obtenerHistorial } from '../api'
import { ETIQUETA_TIPO_CRITERIO, type DocumentoCriterio, type TipoCriterio } from '../types'
import DocumentoActivo from './DocumentoActivo'
import FormularioPin from './FormularioPin'
import FormularioSubirDocumento from './FormularioSubirDocumento'
import HistorialVersiones from './HistorialVersiones'

const TIPOS: TipoCriterio[] = ['clasificacion', 'asignacion_revisor']

function NoHayDocumentoActivo(err: unknown): boolean {
  return err instanceof Error && err.message.includes('No hay un documento activo')
}

function SeccionCriterio({ tipo }: { tipo: TipoCriterio }) {
  const [tienePin, setTienePin] = useState<boolean | null>(null)
  const [mostrarCambiarPin, setMostrarCambiarPin] = useState(false)
  const [documento, setDocumento] = useState<DocumentoCriterio | null>(null)
  const [historial, setHistorial] = useState<DocumentoCriterio[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function cargarDocumentos() {
    setCargando(true)
    setError(null)
    Promise.all([
      obtenerDocumentoActivo(tipo).catch((err) => {
        if (NoHayDocumentoActivo(err)) return null
        throw err
      }),
      obtenerHistorial(tipo),
    ])
      .then(([doc, hist]) => {
        setDocumento(doc)
        setHistorial(hist)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar el documento'))
      .finally(() => setCargando(false))
  }

  useEffect(() => {
    obtenerEstadoPin()
      .then((r) => setTienePin(r.tiene_pin))
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo consultar el estado del PIN'))
    cargarDocumentos()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tipo])

  function handleDocumentoSubido(nuevo: DocumentoCriterio) {
    setDocumento(nuevo)
    cargarDocumentos()
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

      <h2 className="cab-grupo-titulo">Documento activo</h2>
      <DocumentoActivo tipo={tipo} documento={documento} />

      {tienePin && (
        <>
          <h2 className="cab-grupo-titulo">Subir nueva versión</h2>
          <FormularioSubirDocumento tipo={tipo} onSubido={handleDocumentoSubido} />
        </>
      )}

      <h2 className="cab-grupo-titulo">Historial de versiones</h2>
      <HistorialVersiones historial={historial} />
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
        <SeccionCriterio key={tipoActivo} tipo={tipoActivo} />
      </div>
    </div>
  )
}

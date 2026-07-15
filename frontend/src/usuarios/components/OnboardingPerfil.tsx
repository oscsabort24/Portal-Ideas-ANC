import { useEffect, useState, type FormEvent } from 'react'
import { crearUsuario, listarDepartamentos, listarPuestos, listarUsuarios, obtenerUsuarioPorCorreo } from '../api'
import {
  ETIQUETA_COMPANIA,
  ETIQUETA_PAIS,
  type CompaniaUsuario,
  type Departamento,
  type PaisUsuario,
  type Puesto,
  type Usuario,
} from '../types'

const PAISES: PaisUsuario[] = ['CR', 'GT', 'NI', 'PE']
const COMPANIAS: CompaniaUsuario[] = ['ANC_CAR', 'RENTING', 'RENTAS_INT']

/**
 * Formulario de primera vez tras login con Microsoft para una cuenta que
 * todavía no tiene Usuario en nuestra BD (GET /usuarios/por-correo -> 404).
 * Nombre y correo vienen fijos del token de MSAL (no editables) — el resto
 * es el mismo cuerpo de campos que FormularioPersona.tsx en modo "crear",
 * sin selector de rol (el backend fuerza colaborador por defecto).
 */
export default function OnboardingPerfil({
  nombre,
  correo,
  onCompletado,
}: {
  nombre: string
  correo: string
  onCompletado: (usuario: Usuario) => void
}) {
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [puestos, setPuestos] = useState<Puesto[]>([])
  const [personas, setPersonas] = useState<Usuario[]>([])
  const [cargando, setCargando] = useState(true)

  const [pais, setPais] = useState<PaisUsuario | ''>('')
  const [compania, setCompania] = useState<CompaniaUsuario | ''>('')
  const [departamentoId, setDepartamentoId] = useState<string>('')
  const [puestoId, setPuestoId] = useState<string>('')
  const [reportaAId, setReportaAId] = useState<string>('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([listarDepartamentos(), listarPuestos(), listarUsuarios()])
      .then(([deps, puestosCargados, usuarios]) => {
        setDepartamentos(deps)
        setPuestos(puestosCargados)
        setPersonas(usuarios)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar el formulario'))
      .finally(() => setCargando(false))
  }, [])

  const puestosDelDepartamento = departamentoId
    ? puestos.filter((p) => p.departamento_id === Number(departamentoId))
    : []

  function handleCambioDepartamento(valor: string) {
    setDepartamentoId(valor)
    setPuestoId('')
  }

  const camposObligatoriosCompletos = pais && compania && puestoId

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!camposObligatoriosCompletos) return

    setEnviando(true)
    setError(null)
    try {
      await crearUsuario({
        nombre,
        correo,
        pais: pais as PaisUsuario,
        compania: compania as CompaniaUsuario,
        departamento_id: departamentoId ? Number(departamentoId) : null,
        puesto_id: Number(puestoId),
        reporta_a_id: reportaAId ? Number(reportaAId) : null,
      })
      // Se vuelve a consultar por correo (en vez de usar directamente la
      // respuesta de crearUsuario) para que el flujo de resolución del
      // usuario real quede en un solo lugar (usuarios/api.ts:obtenerUsuarioPorCorreo),
      // igual que el resto de AuthProvider.
      const usuarioReal = await obtenerUsuarioPorCorreo(correo)
      onCompletado(usuarioReal)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo completar tu perfil')
    } finally {
      setEnviando(false)
    }
  }

  if (cargando) return <div className="onboarding-shell"><p>Cargando...</p></div>

  return (
    <div className="onboarding-shell">
      <form className="form-card" onSubmit={handleSubmit}>
        <h1 className="page-title">Completa tu perfil</h1>
        <p className="nota-temporal">
          Es la primera vez que inicias sesión — necesitamos algunos datos antes de continuar.
        </p>

        <div className="form-field">
          <label className="form-label">Nombre</label>
          <input className="form-input" value={nombre} disabled readOnly />
        </div>

        <div className="form-field">
          <label className="form-label">Correo</label>
          <input className="form-input" value={correo} disabled readOnly />
        </div>

        <div className="form-row">
          <div className="form-field">
            <label className="form-label" htmlFor="pais">País</label>
            <select id="pais" className="form-input" value={pais} onChange={(e) => setPais(e.target.value as PaisUsuario)}>
              <option value="">Selecciona un país</option>
              {PAISES.map((p) => (
                <option key={p} value={p}>{ETIQUETA_PAIS[p]}</option>
              ))}
            </select>
          </div>

          <div className="form-field">
            <label className="form-label" htmlFor="compania">Compañía</label>
            <select
              id="compania"
              className="form-input"
              value={compania}
              onChange={(e) => setCompania(e.target.value as CompaniaUsuario)}
            >
              <option value="">Selecciona una compañía</option>
              {COMPANIAS.map((c) => (
                <option key={c} value={c}>{ETIQUETA_COMPANIA[c]}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="departamento">Departamento</label>
          <select
            id="departamento"
            className="form-input"
            value={departamentoId}
            onChange={(e) => handleCambioDepartamento(e.target.value)}
          >
            <option value="">Sin asignar</option>
            {departamentos.map((d) => (
              <option key={d.id} value={d.id}>{d.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="puesto">Puesto</label>
          <select
            id="puesto"
            className="form-input"
            value={puestoId}
            onChange={(e) => setPuestoId(e.target.value)}
            disabled={!departamentoId}
          >
            <option value="">{departamentoId ? 'Selecciona un puesto' : 'Elige primero un departamento'}</option>
            {puestosDelDepartamento.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="reportaA">Reporta a</label>
          <select id="reportaA" className="form-input" value={reportaAId} onChange={(e) => setReportaAId(e.target.value)}>
            <option value="">Sin asignar</option>
            {personas.map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
          </select>
        </div>

        <p className="nota-temporal">Inicias como colaborador. Un administrador puede cambiar tu rol después.</p>

        {error && <p className="form-error">{error}</p>}

        <div className="form-row">
          <button type="submit" className="btn-primary" disabled={!camposObligatoriosCompletos || enviando}>
            {enviando ? 'Guardando...' : 'Continuar'}
          </button>
        </div>
      </form>
    </div>
  )
}

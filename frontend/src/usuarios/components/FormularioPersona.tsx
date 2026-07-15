import { useState, type FormEvent } from 'react'
import { actualizarUsuario, crearUsuario } from '../api'
import {
  DESCRIPCION_ROL,
  ETIQUETA_COMPANIA,
  ETIQUETA_PAIS,
  ETIQUETA_ROL,
  type CompaniaUsuario,
  type Departamento,
  type PaisUsuario,
  type Puesto,
  type RolUsuario,
  type Usuario,
} from '../types'

const ROLES: RolUsuario[] = ['colaborador', 'encargado_area', 'gerente', 'admin']
const PAISES: PaisUsuario[] = ['CR', 'GT', 'NI', 'PE']
const COMPANIAS: CompaniaUsuario[] = ['ANC_CAR', 'RENTING', 'RENTAS_INT']

export default function FormularioPersona({
  departamentos,
  puestos,
  personas,
  modo = 'crear',
  personaEditando,
  onCreada,
  onEditada,
  onCancelar,
}: {
  departamentos: Departamento[]
  puestos: Puesto[]
  personas: Usuario[]
  modo?: 'crear' | 'editar'
  personaEditando?: Usuario
  onCreada?: (usuario: Usuario) => void
  onEditada?: (usuario: Usuario) => void
  onCancelar?: () => void
}) {
  const [nombre, setNombre] = useState(personaEditando?.nombre ?? '')
  const [correo, setCorreo] = useState(personaEditando?.correo ?? '')
  const [rol, setRol] = useState<RolUsuario>(personaEditando?.rol ?? 'colaborador')
  const [pais, setPais] = useState<PaisUsuario | ''>(personaEditando?.pais ?? '')
  const [compania, setCompania] = useState<CompaniaUsuario | ''>(personaEditando?.compania ?? '')
  const [departamentoId, setDepartamentoId] = useState<string>(
    personaEditando?.departamento_id ? String(personaEditando.departamento_id) : ''
  )
  const [puestoId, setPuestoId] = useState<string>(
    personaEditando?.puesto_id ? String(personaEditando.puesto_id) : ''
  )
  const [reportaAId, setReportaAId] = useState<string>(
    personaEditando?.reporta_a_id ? String(personaEditando.reporta_a_id) : ''
  )
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const puestosDelDepartamento = departamentoId
    ? puestos.filter((p) => p.departamento_id === Number(departamentoId))
    : []

  function handleCambioDepartamento(valor: string) {
    setDepartamentoId(valor)
    setPuestoId('') // el puesto depende del departamento — se limpia al cambiarlo
  }

  const camposObligatoriosCompletos =
    nombre.trim() && correo.trim() && (modo === 'editar' || (pais && compania && puestoId))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!camposObligatoriosCompletos) return

    setEnviando(true)
    setError(null)
    try {
      if (modo === 'editar' && personaEditando) {
        const usuario = await actualizarUsuario(personaEditando.id, {
          nombre: nombre.trim(),
          correo: correo.trim(),
          rol,
          pais: pais || undefined,
          compania: compania || undefined,
          departamento_id: departamentoId ? Number(departamentoId) : null,
          puesto_id: puestoId ? Number(puestoId) : null,
          reporta_a_id: reportaAId ? Number(reportaAId) : null,
        })
        onEditada?.(usuario)
      } else {
        const usuario = await crearUsuario({
          nombre: nombre.trim(),
          correo: correo.trim(),
          pais: pais as PaisUsuario,
          compania: compania as CompaniaUsuario,
          departamento_id: departamentoId ? Number(departamentoId) : null,
          puesto_id: Number(puestoId),
          reporta_a_id: reportaAId ? Number(reportaAId) : null,
        })
        onCreada?.(usuario)
        setNombre('')
        setCorreo('')
        setPais('')
        setCompania('')
        setDepartamentoId('')
        setPuestoId('')
        setReportaAId('')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar la persona')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="form-card" onSubmit={handleSubmit}>
      <div className="form-field">
        <label className="form-label" htmlFor="nombre">Nombre</label>
        <input
          id="nombre"
          className="form-input"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Ej. María Fernández"
        />
      </div>

      <div className="form-field">
        <label className="form-label" htmlFor="correo">Correo</label>
        <input
          id="correo"
          type="email"
          className="form-input"
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
          placeholder="nombre@grupoanc.com"
        />
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

      <div className="form-row">
        {modo === 'editar' && (
          <div className="form-field">
            <label className="form-label" htmlFor="rol">Rol</label>
            <select id="rol" className="form-input" value={rol} onChange={(e) => setRol(e.target.value as RolUsuario)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{ETIQUETA_ROL[r]}</option>
              ))}
            </select>
            <p className="form-help">{DESCRIPCION_ROL[rol]}</p>
          </div>
        )}

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

      {modo === 'crear' && (
        <p className="nota-temporal">
          Las personas nuevas inician como colaborador. Un administrador puede cambiar el rol después.
        </p>
      )}

      <div className="form-field">
        <label className="form-label" htmlFor="reportaA">Reporta a</label>
        <select
          id="reportaA"
          className="form-input"
          value={reportaAId}
          onChange={(e) => setReportaAId(e.target.value)}
        >
          <option value="">Sin asignar</option>
          {personas
            .filter((p) => p.id !== personaEditando?.id)
            .map((p) => (
              <option key={p.id} value={p.id}>{p.nombre}</option>
            ))}
        </select>
      </div>

      {error && <p className="form-error">{error}</p>}

      <div className="form-row">
        <button type="submit" className="btn-primary" disabled={!camposObligatoriosCompletos || enviando}>
          {enviando ? 'Guardando...' : modo === 'editar' ? 'Guardar cambios' : 'Agregar persona'}
        </button>
        {modo === 'editar' && (
          <button type="button" className="btn-secundario" onClick={onCancelar}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}

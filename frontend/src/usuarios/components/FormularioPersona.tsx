import { useState, type FormEvent } from 'react'
import { actualizarUsuario, crearUsuario } from '../api'
import { ETIQUETA_ROL, type Departamento, type RolUsuario, type Usuario } from '../types'

const ROLES: RolUsuario[] = ['colaborador', 'encargado_area', 'gerente', 'admin']

export default function FormularioPersona({
  departamentos,
  personas,
  modo = 'crear',
  personaEditando,
  onCreada,
  onEditada,
  onCancelar,
}: {
  departamentos: Departamento[]
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
  const [departamentoId, setDepartamentoId] = useState<string>(
    personaEditando?.departamento_id ? String(personaEditando.departamento_id) : ''
  )
  const [reportaAId, setReportaAId] = useState<string>(
    personaEditando?.reporta_a_id ? String(personaEditando.reporta_a_id) : ''
  )
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nombre.trim() || !correo.trim()) return

    setEnviando(true)
    setError(null)
    try {
      if (modo === 'editar' && personaEditando) {
        const usuario = await actualizarUsuario(personaEditando.id, {
          nombre: nombre.trim(),
          correo: correo.trim(),
          rol,
          departamento_id: departamentoId ? Number(departamentoId) : null,
          reporta_a_id: reportaAId ? Number(reportaAId) : null,
        })
        onEditada?.(usuario)
      } else {
        const usuario = await crearUsuario({
          nombre: nombre.trim(),
          correo: correo.trim(),
          departamento_id: departamentoId ? Number(departamentoId) : null,
          reporta_a_id: reportaAId ? Number(reportaAId) : null,
        })
        onCreada?.(usuario)
        setNombre('')
        setCorreo('')
        setDepartamentoId('')
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
        {modo === 'editar' && (
          <div className="form-field">
            <label className="form-label" htmlFor="rol">Rol</label>
            <select id="rol" className="form-input" value={rol} onChange={(e) => setRol(e.target.value as RolUsuario)}>
              {ROLES.map((r) => (
                <option key={r} value={r}>{ETIQUETA_ROL[r]}</option>
              ))}
            </select>
          </div>
        )}

        <div className="form-field">
          <label className="form-label" htmlFor="departamento">Departamento</label>
          <select
            id="departamento"
            className="form-input"
            value={departamentoId}
            onChange={(e) => setDepartamentoId(e.target.value)}
          >
            <option value="">Sin asignar</option>
            {departamentos.map((d) => (
              <option key={d.id} value={d.id}>{d.nombre}</option>
            ))}
          </select>
        </div>
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
        <button type="submit" className="btn-primary" disabled={!nombre.trim() || !correo.trim() || enviando}>
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

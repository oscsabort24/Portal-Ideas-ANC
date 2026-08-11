import { useEffect, useMemo, useState } from 'react'
import { FiPlus, FiUser } from 'react-icons/fi'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { actualizarUsuario, listarDepartamentos, listarPuestos, listarUsuarios } from '../api'
import { DESCRIPCION_ROL, ETIQUETA_ROL, ROLES_ORDENADOS, type Departamento, type Puesto, type Usuario } from '../types'
import FormularioPersona from './FormularioPersona'

function normalizar(texto: string): string {
  return Array.from(texto.normalize('NFD'))
    .filter((c) => {
      const codigo = c.codePointAt(0) ?? 0
      return codigo < 0x0300 || codigo > 0x036f
    })
    .join('')
    .toLowerCase()
}

export default function ListaPersonas() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const [personas, setPersonas] = useState<Usuario[]>([])
  const [departamentos, setDepartamentos] = useState<Departamento[]>([])
  const [puestos, setPuestos] = useState<Puesto[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mostrarFormulario, setMostrarFormulario] = useState(false)
  const [editandoId, setEditandoId] = useState<number | null>(null)
  const [busqueda, setBusqueda] = useState('')
  const [departamentoFiltro, setDepartamentoFiltro] = useState('')

  useEffect(() => {
    Promise.all([listarUsuarios(), listarDepartamentos(), listarPuestos()])
      .then(([usuarios, deps, puestosCargados]) => {
        setPersonas(usuarios)
        setDepartamentos(deps)
        setPuestos(puestosCargados)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar las personas'))
      .finally(() => setCargando(false))
  }, [])

  function nombreDepartamento(id: number | null): string {
    if (id === null) return '—'
    return departamentos.find((d) => d.id === id)?.nombre ?? '—'
  }

  function nombreReportaA(id: number | null): string {
    if (id === null) return '—'
    return personas.find((p) => p.id === id)?.nombre ?? '—'
  }

  function handleCreada(usuario: Usuario) {
    setPersonas((prev) => [...prev, usuario])
    setMostrarFormulario(false)
  }

  function handleEditada(usuario: Usuario) {
    setPersonas((prev) => prev.map((p) => (p.id === usuario.id ? usuario : p)))
    setEditandoId(null)
  }

  async function handleToggleActivo(persona: Usuario) {
    if (persona.activo) {
      const confirmado = window.confirm(
        `¿Desactivar a ${persona.nombre}? No podrá seguir usando el sistema, pero sus ideas se conservan.`
      )
      if (!confirmado) return
    }
    try {
      const actualizado = await actualizarUsuario(persona.id, { activo: !persona.activo })
      setPersonas((prev) => prev.map((p) => (p.id === actualizado.id ? actualizado : p)))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo actualizar el estado de la persona')
    }
  }

  const personasFiltradas = useMemo(() => {
    const busquedaNormalizada = normalizar(busqueda.trim())
    return personas.filter((p) => {
      const coincideNombre = !busquedaNormalizada || normalizar(p.nombre).includes(busquedaNormalizada)
      const coincideDepartamento =
        !departamentoFiltro || p.departamento_id === Number(departamentoFiltro)
      return coincideNombre && coincideDepartamento
    })
  }, [personas, busqueda, departamentoFiltro])

  if (cargando) return <p>Cargando...</p>

  return (
    <div>
      <div className="leyenda-roles">
        {ROLES_ORDENADOS.map((r) => (
          <div key={r} className="leyenda-roles-item">
            <strong>{ETIQUETA_ROL[r]}:</strong> {DESCRIPCION_ROL[r]}
          </div>
        ))}
      </div>

      <div className="tab-actions-row">
        <p className="nota-temporal">
          Registro manual temporal — reemplazado por inicio de sesión con Microsoft (Entra ID) cuando esté disponible.
        </p>
        <button
          className="btn-primary"
          onClick={() => {
            setEditandoId(null)
            setMostrarFormulario((v) => !v)
          }}
        >
          <FiPlus /> Agregar persona
        </button>
      </div>

      {mostrarFormulario && (
        <FormularioPersona
          departamentos={departamentos}
          puestos={puestos}
          personas={personas}
          onCreada={handleCreada}
        />
      )}

      {error && <p className="form-error">{error}</p>}

      <div className="form-row filtros-personas">
        <div className="form-field">
          <label className="form-label" htmlFor="busqueda-nombre">Buscar por nombre</label>
          <input
            id="busqueda-nombre"
            className="form-input"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Ej. Ana"
          />
        </div>
        <div className="form-field">
          <label className="form-label" htmlFor="filtro-departamento">Departamento</label>
          <select
            id="filtro-departamento"
            className="form-input"
            value={departamentoFiltro}
            onChange={(e) => setDepartamentoFiltro(e.target.value)}
          >
            <option value="">Todos los departamentos</option>
            {departamentos.map((d) => (
              <option key={d.id} value={d.id}>{d.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      {personasFiltradas.length === 0 ? (
        <p className="cab-vacio">No se encontraron personas con estos filtros.</p>
      ) : (
        <div className="tabla-personas">
          {personasFiltradas.map((p) =>
            editandoId === p.id ? (
              <FormularioPersona
                key={p.id}
                modo="editar"
                personaEditando={p}
                departamentos={departamentos}
                puestos={puestos}
                personas={personas}
                onEditada={handleEditada}
                onCancelar={() => setEditandoId(null)}
              />
            ) : (
              <div key={p.id} className="persona-card">
                <div className="persona-card-icon">
                  <FiUser />
                </div>
                <div className="persona-card-info">
                  <div className="persona-card-nombre">{p.nombre}</div>
                  <div className="persona-card-correo">{p.correo}</div>
                </div>
                <div className="persona-card-meta">
                  <span className="persona-meta-label">Departamento</span>
                  <span>{nombreDepartamento(p.departamento_id)}</span>
                </div>
                <div className="persona-card-meta">
                  <span className="persona-meta-label">Rol</span>
                  <span className="rol-badge">{ETIQUETA_ROL[p.rol]}</span>
                </div>
                <div className="persona-card-meta">
                  <span className="persona-meta-label">Reporta a</span>
                  <span>{nombreReportaA(p.reporta_a_id)}</span>
                </div>
                <div className="persona-card-estado">
                  <span className={`activo-badge ${p.activo ? 'activo' : 'inactivo'}`}>
                    {p.activo ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
                <div className="persona-card-actions">
                  {esAdmin && (
                    <>
                      <button
                        className="btn-small"
                        onClick={() => {
                          setMostrarFormulario(false)
                          setEditandoId(p.id)
                        }}
                      >
                        Editar
                      </button>
                      <button
                        className={`btn-small ${p.activo ? 'peligro' : 'exito'}`}
                        onClick={() => handleToggleActivo(p)}
                      >
                        {p.activo ? 'Desactivar' : 'Reactivar'}
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          )}
        </div>
      )}
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useUsuarioActual } from '../../core/UsuarioActualContext'
import { guardarPermisosRol, listarPermisosRol } from '../api'
import {
  DESCRIPCION_ROL,
  ETIQUETA_PERMISO,
  ETIQUETA_ROL,
  PERMISOS_ORDENADOS,
  ROLES_CONFIGURABLES,
  ROLES_ORDENADOS,
} from '../types'
import type { ClavePermiso, PermisoRol, RolUsuario } from '../types'

function ReferenciaRoles() {
  return (
    <div>
      <p className="form-help" style={{ marginBottom: 16 }}>
        Referencia de qué puede hacer cada rol en el sistema. Los roles se acumulan: cada uno
        incluye todo lo del anterior, además de lo propio.
      </p>

      <div className="tabla-roles-wrapper">
        <table className="tabla-roles">
          <thead>
            <tr>
              <th>Rol</th>
              <th>Qué puede hacer</th>
            </tr>
          </thead>
          <tbody>
            {ROLES_ORDENADOS.map((rol) => (
              <tr key={rol}>
                <td>
                  <span className="rol-badge">{ETIQUETA_ROL[rol]}</span>
                </td>
                <td>{DESCRIPCION_ROL[rol]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="form-help" style={{ marginTop: 16 }}>
        Aparte de estos 4 roles, ser Portfolio Owner da acceso a ver los documentos de las ideas
        de los departamentos que tenga asignados, sin importar el rol de la persona.
      </p>
    </div>
  )
}

/** Lo que ve quien no es administrador en la pestaña de permisos.
 *
 * La pestaña se sigue mostrando a todos a propósito: saber que los permisos
 * son configurables —y por quién— es información útil para cualquiera que se
 * pregunte por qué no ve algo. Lo que no se muestra es la grilla.
 *
 * No es solo cosmético: GET /permisos-rol ya exigía admin
 * (permisos/router.py), así que hasta ahora un no-admin que abría esta
 * pestaña recibía un 403 crudo en pantalla. Nunca hubo fuga de datos, pero
 * la persona veía un error como si algo estuviera roto. */
function NotaPermisosSoloAdmin() {
  return (
    <div>
      <p className="form-help" style={{ marginBottom: 12 }}>
        El sistema tiene <strong>cuatro permisos configurables</strong> que definen qué puede
        hacer cada rol: ver todas las ideas, ver Flow Control, ser elegible como revisor y
        corregir la clasificación de una idea.
      </p>
      <p className="form-help" style={{ marginBottom: 12 }}>
        Su configuración es exclusiva de los administradores, así que esta pantalla es de solo
        lectura para tu rol. Si necesitás un permiso que hoy no tenés, pedíselo a un
        administrador.
      </p>
      <p className="form-help">
        El rol <strong>Administrador</strong> siempre tiene acceso completo y no es configurable.
      </p>
    </div>
  )
}

function clavePermitido(permisos: PermisoRol[], rol: RolUsuario, clave: ClavePermiso): boolean {
  return permisos.find((p) => p.rol === rol && p.clave_permiso === clave)?.permitido ?? false
}

function PermisosConfigurables() {
  const [permisos, setPermisos] = useState<PermisoRol[]>([])
  const [cambios, setCambios] = useState<Map<string, boolean>>(new Map())
  const [cargando, setCargando] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [mensaje, setMensaje] = useState<string | null>(null)

  function cargar() {
    setCargando(true)
    setError(null)
    listarPermisosRol()
      .then(setPermisos)
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudieron cargar los permisos'))
      .finally(() => setCargando(false))
  }

  useEffect(cargar, [])

  function valorActual(rol: RolUsuario, clave: ClavePermiso): boolean {
    const clave2 = `${rol}:${clave}`
    return cambios.has(clave2) ? Boolean(cambios.get(clave2)) : clavePermitido(permisos, rol, clave)
  }

  function alternar(rol: RolUsuario, clave: ClavePermiso) {
    const clave2 = `${rol}:${clave}`
    const nuevo = new Map(cambios)
    nuevo.set(clave2, !valorActual(rol, clave))
    setCambios(nuevo)
    setMensaje(null)
  }

  async function guardar() {
    setGuardando(true)
    setError(null)
    setMensaje(null)
    try {
      const payload = ROLES_CONFIGURABLES.flatMap((rol) =>
        PERMISOS_ORDENADOS.map((clave) => ({
          rol,
          clave_permiso: clave,
          permitido: valorActual(rol, clave),
        })),
      )
      const actualizados = await guardarPermisosRol(payload)
      setPermisos(actualizados)
      setCambios(new Map())
      setMensaje('Permisos guardados.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudieron guardar los permisos')
    } finally {
      setGuardando(false)
    }
  }

  if (cargando) return <p>Cargando permisos...</p>

  return (
    <div>
      <p className="form-help" style={{ marginBottom: 16 }}>
        Activá o desactivá permisos por rol. <strong>Administrador</strong> siempre tiene acceso
        completo — no es configurable, para evitar quedarse sin acceso al propio panel que sirve
        para corregir este tipo de error.
      </p>

      {error && <p className="form-error">{error}</p>}
      {mensaje && <p className="form-help">{mensaje}</p>}

      <div className="tabla-roles-wrapper">
        <table className="tabla-roles">
          <thead>
            <tr>
              <th>Permiso</th>
              {ROLES_CONFIGURABLES.map((rol) => (
                <th key={rol}>{ETIQUETA_ROL[rol]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PERMISOS_ORDENADOS.map((clave) => (
              <tr key={clave}>
                <td>{ETIQUETA_PERMISO[clave]}</td>
                {ROLES_CONFIGURABLES.map((rol) => (
                  <td key={rol} style={{ textAlign: 'center' }}>
                    <input
                      type="checkbox"
                      id={`permiso-${clave}-${rol}`}
                      aria-label={`${ETIQUETA_PERMISO[clave]} — ${ETIQUETA_ROL[rol]}`}
                      checked={valorActual(rol, clave)}
                      onChange={() => alternar(rol, clave)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="button"
        className="btn-primario"
        style={{ marginTop: 16 }}
        onClick={guardar}
        disabled={guardando || cambios.size === 0}
      >
        {guardando ? 'Guardando...' : 'Guardar cambios'}
      </button>
    </div>
  )
}

export default function RolesView() {
  const [pestana, setPestana] = useState<'referencia' | 'permisos'>('referencia')
  // El gate real de la grilla vive en el backend (requerir_admin en GET y PUT
  // de /permisos-rol). Esto decide qué se dibuja, no qué se autoriza: si
  // alguien fuerza esAdmin en el cliente, la petición igual vuelve 403.
  const esAdmin = useUsuarioActual().rol === 'admin'

  return (
    <div>
      <h1 className="page-title">Roles y permisos</h1>

      <div className="tabs-row" style={{ marginBottom: 16 }}>
        <button
          type="button"
          className={`tab-button ${pestana === 'referencia' ? 'active' : ''}`}
          onClick={() => setPestana('referencia')}
        >
          Referencia de roles
        </button>
        <button
          type="button"
          className={`tab-button ${pestana === 'permisos' ? 'active' : ''}`}
          onClick={() => setPestana('permisos')}
        >
          Permisos configurables
        </button>
      </div>

      <div className="tab-content">
        {pestana === 'referencia' ? (
          <ReferenciaRoles />
        ) : esAdmin ? (
          <PermisosConfigurables />
        ) : (
          <NotaPermisosSoloAdmin />
        )}
      </div>
    </div>
  )
}

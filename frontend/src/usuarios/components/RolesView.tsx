import { DESCRIPCION_ROL, ETIQUETA_ROL, ROLES_ORDENADOS } from '../types'

export default function RolesView() {
  return (
    <div>
      <h1 className="page-title">Roles y permisos</h1>
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
        Aparte de estos 4 roles, ser miembro de un Comité (CAB) da acceso a ver los documentos de
        las ideas asignadas a ese comité, sin importar el rol de la persona.
      </p>
    </div>
  )
}

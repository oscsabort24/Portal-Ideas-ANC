import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  FiAward,
  FiBell,
  FiBriefcase,
  FiCheckSquare,
  FiChevronDown,
  FiChevronRight,
  FiClipboard,
  FiFileText,
  FiGrid,
  FiHome,
  FiKey,
  FiPlus,
  FiShield,
  FiTag,
  FiUsers,
} from 'react-icons/fi'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import { useEsMiembroCab } from '../usuarios/hooks/useEsMiembroCab'
import { useMisPermisos } from '../usuarios/hooks/useMisPermisos'

const RUTAS_ORGANIZACION = [
  '/organizacion/roles',
  '/departamentos',
  '/puestos',
  '/comite-cab',
  '/criterios',
  '/notificaciones',
]

export default function Sidebar() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const { veFlowControl, esRevisorElegible } = useMisPermisos()
  const puedeRevisar = esAdmin || esRevisorElegible
  const { esMiembro: esMiembroCab } = useEsMiembroCab()
  const location = useLocation()

  const [organizacionAbierta, setOrganizacionAbierta] = useState(() =>
    RUTAS_ORGANIZACION.includes(location.pathname),
  )

  return (
    <nav className="app-sidebar">
      <div className="sidebar-section">
        <NavLink to="/" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} end>
          <FiHome className="sidebar-link-icon" />
          Inicio
        </NavLink>
      </div>

      {(esAdmin || veFlowControl) && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Trazabilidad</div>
          <NavLink to="/flow-control" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiGrid className="sidebar-link-icon" />
            Flow Control
          </NavLink>
          <NavLink to="/admin/ideas" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiClipboard className="sidebar-link-icon" />
            Panel de administración
          </NavLink>
        </div>
      )}

      <div className="sidebar-section">
        <div className="sidebar-section-title">Colaborador</div>
        <NavLink to="/ideas/nueva" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
          <FiPlus className="sidebar-link-icon" />
          Nueva idea
        </NavLink>
        <NavLink to="/ideas" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`} end>
          <FiFileText className="sidebar-link-icon" />
          Mis ideas
        </NavLink>
      </div>

      {puedeRevisar && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Revisión de área</div>
          <NavLink to="/revision" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiCheckSquare className="sidebar-link-icon" />
            Por revisar
          </NavLink>
          {esAdmin && (
            <NavLink to="/clasificacion" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
              <FiTag className="sidebar-link-icon" />
              Ideas por clasificar
            </NavLink>
          )}
        </div>
      )}

      {(esAdmin || esMiembroCab) && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Comité (CAB)</div>
          <NavLink to="/comites" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiCheckSquare className="sidebar-link-icon" />
            Cola del comité
          </NavLink>
        </div>
      )}

      {esAdmin && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Usuarios</div>
          <NavLink to="/usuarios" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiUsers className="sidebar-link-icon" />
            Usuarios
          </NavLink>
        </div>
      )}

      <div className="sidebar-section">
        <button
          type="button"
          className="sidebar-section-title sidebar-acordeon-boton"
          onClick={() => setOrganizacionAbierta((prev) => !prev)}
          aria-expanded={organizacionAbierta}
        >
          {organizacionAbierta ? (
            <FiChevronDown className="sidebar-acordeon-icono" />
          ) : (
            <FiChevronRight className="sidebar-acordeon-icono" />
          )}
          Organización
        </button>

        {organizacionAbierta && (
          <>
            <NavLink to="/organizacion/roles" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
              <FiKey className="sidebar-link-icon" />
              Roles y permisos
            </NavLink>
            {esAdmin && (
              <>
                <NavLink to="/departamentos" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
                  <FiBriefcase className="sidebar-link-icon" />
                  Departamentos
                </NavLink>
                <NavLink to="/puestos" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
                  <FiTag className="sidebar-link-icon" />
                  Puestos
                </NavLink>
                <NavLink to="/comite-cab" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
                  <FiAward className="sidebar-link-icon" />
                  Portfolio Owners
                </NavLink>
                <NavLink to="/criterios" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
                  <FiShield className="sidebar-link-icon" />
                  Criterios IA
                </NavLink>
                <NavLink to="/notificaciones" className={({ isActive }) => `sidebar-link sidebar-sublink ${isActive ? 'active' : ''}`}>
                  <FiBell className="sidebar-link-icon" />
                  Notificaciones
                </NavLink>
              </>
            )}
          </>
        )}
      </div>
    </nav>
  )
}

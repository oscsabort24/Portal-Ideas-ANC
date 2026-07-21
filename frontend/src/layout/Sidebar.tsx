import { NavLink } from 'react-router-dom'
import { FiBell, FiCheckSquare, FiClipboard, FiFileText, FiPlus, FiShield, FiTag, FiUsers } from 'react-icons/fi'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import { useEsMiembroCab } from '../usuarios/hooks/useEsMiembroCab'

export default function Sidebar() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'
  const puedeRevisar = esAdmin || usuarioActual.rol === 'encargado_area' || usuarioActual.rol === 'gerente'
  const { esMiembro: esMiembroCab } = useEsMiembroCab()

  return (
    <nav className="app-sidebar">
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
          <div className="sidebar-section-title">Administración</div>
          <NavLink to="/admin/ideas" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiClipboard className="sidebar-link-icon" />
            Panel de administración
          </NavLink>
          <NavLink to="/usuarios" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiUsers className="sidebar-link-icon" />
            Usuarios
          </NavLink>
        </div>
      )}

      {esAdmin && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Clasificación</div>
          <NavLink to="/clasificacion" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiTag className="sidebar-link-icon" />
            Ideas por clasificar
          </NavLink>
        </div>
      )}

      {esAdmin && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Criterios IA</div>
          <NavLink to="/criterios" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiShield className="sidebar-link-icon" />
            Documentos de criterios
          </NavLink>
        </div>
      )}

      {esAdmin && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Notificaciones</div>
          <NavLink to="/notificaciones" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiBell className="sidebar-link-icon" />
            Escalamiento por inactividad
          </NavLink>
        </div>
      )}
    </nav>
  )
}

import { NavLink } from 'react-router-dom'
import { FiFileText, FiLock, FiPlus, FiUsers } from 'react-icons/fi'

export default function Sidebar() {
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

      <div className="sidebar-section">
        <div className="sidebar-section-title">Revisión de área</div>
        {/* Depende del módulo revision/, que todavía no existe. Deshabilitado hasta que se construya. */}
        <span className="sidebar-link disabled">
          <FiLock className="sidebar-link-icon" />
          Por revisar
        </span>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">Comité (CAB)</div>
        {/* Depende del módulo comites/, que todavía no existe. Deshabilitado hasta que se construya. */}
        <span className="sidebar-link disabled">
          <FiLock className="sidebar-link-icon" />
          Cola del comité
        </span>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-title">Administración</div>
        <NavLink to="/usuarios" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
          <FiUsers className="sidebar-link-icon" />
          Usuarios
        </NavLink>
      </div>
    </nav>
  )
}

import { NavLink } from 'react-router-dom'
import { FiFileText, FiLock, FiPlus, FiShield, FiUsers } from 'react-icons/fi'
import { useUsuarioActual } from '../core/UsuarioActualContext'

export default function Sidebar() {
  const usuarioActual = useUsuarioActual()
  const esAdmin = usuarioActual.rol === 'admin'

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

      {esAdmin && (
        <div className="sidebar-section">
          <div className="sidebar-section-title">Criterios IA</div>
          <NavLink to="/criterios" className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}>
            <FiShield className="sidebar-link-icon" />
            Documentos de criterios
          </NavLink>
        </div>
      )}
    </nav>
  )
}

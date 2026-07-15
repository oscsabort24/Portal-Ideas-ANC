import { useMsal } from '@azure/msal-react'
import { FiLock } from 'react-icons/fi'
import { loginRequest } from './authConfig'

function OndasDecorativas() {
  return (
    <svg
      className="login-ondas"
      viewBox="0 0 720 1080"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
    >
      <path
        d="M0,900 C150,760 250,980 400,860 C550,740 650,900 720,800"
        fill="none"
        stroke="#1E4A73"
        strokeWidth="1.5"
        opacity="0.5"
      />
      <path
        d="M0,980 C160,860 260,1040 420,920 C580,800 680,960 720,880"
        fill="none"
        stroke="#E8ECEF"
        strokeWidth="1.5"
        opacity="0.5"
      />
    </svg>
  )
}

function IconoMicrosoft() {
  return (
    <svg className="login-ms-icon" viewBox="0 0 21 21" aria-hidden="true">
      <rect x="1" y="1" width="9" height="9" fill="#f25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
      <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
      <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
    </svg>
  )
}

export default function LoginScreen() {
  const { instance } = useMsal()

  return (
    <div className="login-screen">
      <div className="login-panel-izq">
        <OndasDecorativas />
        <div className="login-logo-circle">
          <img className="login-logo-img" src="/assets/logo.jpg" alt="Grupo ANC" />
        </div>
        <h1 className="login-brand-title">Portafolio de Iniciativas</h1>
        <p className="login-brand-subtitle">Cada idea, un camino claro hacia la ejecución.</p>
        <p className="login-brand-footer">Grupo ANC</p>
      </div>

      <div className="login-divider" />

      <div className="login-panel-der">
        <div className="login-contenido">
          <p className="login-bienvenido">BIENVENIDO</p>
          <h2 className="login-heading">Inicia sesión</h2>
          <p className="login-desc">
            Usa tu cuenta corporativa de Microsoft para acceder al portafolio de iniciativas.
          </p>

          <button className="login-ms-btn" onClick={() => instance.loginRedirect(loginRequest)}>
            <IconoMicrosoft />
            Continuar con Microsoft
          </button>

          <p className="login-lock-note">
            <FiLock /> Acceso exclusivo para colaboradores de Grupo ANC
          </p>
        </div>

        <p className="login-footer-der">Transformación Digital · Grupo ANC · v1.0</p>
      </div>
    </div>
  )
}

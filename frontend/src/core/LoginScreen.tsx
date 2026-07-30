import { useMsal } from '@azure/msal-react'
import { FiLock } from 'react-icons/fi'
import { azureAdConfigurado, loginRequest } from './authConfig'
import { devLogin } from '../usuarios/api'
import { CLAVE_DEV_LOGIN_HECHO } from './UsuarioActualContext'

// TEMPORAL — accesos rápidos de prueba, solo para desarrollo local.
// import.meta.env.DEV lo pone Vite en `false` en cualquier build de producción
// (`vite build`), así que este bloque ni siquiera queda en el bundle servido.
// Además, /auth/dev-login solo existe en el backend si ENTORNO=development
// (ver core/dev_router.py) — doble candado, ninguno depende del otro.
const USUARIOS_PRUEBA = [
  { etiqueta: 'Admin', correo: 'oscar.saborio@grupoanc.com' },
  { etiqueta: 'Encargado de Área', correo: 'prueba@anc.com' },
  { etiqueta: 'Colaborador', correo: 'colaborador.prueba.docs@anc-prueba.com' },
  { etiqueta: 'Gerente', correo: 'gerente.prueba@anc-prueba.com' },
]

function AccesosRapidosDev() {
  if (!import.meta.env.DEV) return null

  async function entrarComo(correo: string) {
    try {
      const usuario = await devLogin(correo)
      // Se guarda el usuario completo, no un booleano: window.location.href
      // hace un reload real, que reinicializa USUARIO_ACTUAL desde cero
      // (ver UsuarioActualContext.tsx:usuarioInicial) — así sobrevive el dato,
      // no solo la marca de "ya se logueó".
      sessionStorage.setItem(CLAVE_DEV_LOGIN_HECHO, JSON.stringify(usuario))
      window.location.href = '/'
    } catch (err) {
      console.error('dev-login falló:', err)
      alert('No se pudo entrar como usuario de prueba (¿backend con ENTORNO=development?)')
    }
  }

  return (
    <div
      style={{
        marginTop: '1.5rem',
        padding: '0.75rem',
        border: '1px dashed #d97706',
        borderRadius: '8px',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <p style={{ margin: 0, fontSize: '0.8rem', color: '#d97706' }}>🔧 Accesos de desarrollo</p>
      {USUARIOS_PRUEBA.map((u) => (
        <button
          key={u.correo}
          type="button"
          onClick={() => entrarComo(u.correo)}
          style={{
            padding: '0.4rem 0.75rem',
            fontSize: '0.85rem',
            border: '1px solid #d97706',
            borderRadius: '6px',
            background: 'transparent',
            cursor: 'pointer',
          }}
        >
          {u.etiqueta}
        </button>
      ))}
    </div>
  )
}

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

function BotonMicrosoft() {
  const { instance } = useMsal()
  return (
    <button className="login-ms-btn" onClick={() => instance.loginRedirect(loginRequest)}>
      <IconoMicrosoft />
      Continuar con Microsoft
    </button>
  )
}

export default function LoginScreen() {
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

          {azureAdConfigurado && <BotonMicrosoft />}

          <p className="login-lock-note">
            <FiLock /> Acceso exclusivo para colaboradores de Grupo ANC
          </p>

          <AccesosRapidosDev />
        </div>

        <p className="login-footer-der">Transformación Digital · Grupo ANC · v1.0</p>
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiAlertCircle, FiCheckCircle, FiClipboard, FiFileText, FiPlus, FiUserCheck, FiUsers } from 'react-icons/fi'
import { listarIdeas } from '../ideas/api'
import { misRevisiones, revisionesSinAsignar } from '../revision/api'
import { colaComite } from '../comites/api'
import { useUsuarioActual } from '../core/UsuarioActualContext'
import { useEsMiembroCab } from '../usuarios/hooks/useEsMiembroCab'
import { useMisPermisos } from '../usuarios/hooks/useMisPermisos'
import type { Idea } from '../ideas/types'
import type { RevisionDetalle } from '../revision/types'
import type { TipoCAB } from '../usuarios/types'

const TODOS_TIPOS_CAB: TipoCAB[] = ['innovacion', 'transformacion_digital']

function diasDesde(iso: string): number {
  const dias = (Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60 * 24)
  return Math.max(0, Math.floor(dias))
}

interface DatosPersona {
  // colaborador
  borradorPropio: Idea | null
  // encargado_area / gerente (también puede revisar)
  misPendientesRevisar: number
}

interface DatosSistema {
  total: number
  borrador: number
  enviada: number
  sinAsignar: number | null // null si el rol no tiene acceso (no-admin)
  enComite: number | null // null si no aplica ningún tipo de CAB para este usuario
  aprobadas: number | null
  pendientesPorPersona: { nombre: string; cantidad: number; diasMasAntiguo: number }[] | null // solo admin
}

function useDatosPersona(
  rol: string,
  esRevisorElegible: boolean,
): { datos: DatosPersona | null; cargando: boolean } {
  const [datos, setDatos] = useState<DatosPersona | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    let cancelado = false
    setCargando(true)

    // Admin no tiene un aviso "personal" de revisión: misRevisiones() como
    // admin devuelve TODAS las pendientes del sistema (ver revision/router.py),
    // ese dato ya se muestra agregado en el dashboard de sistema, no como
    // "tenés N pendientes" (sería engañoso — no son necesariamente suyas).
    const pedirBorrador = rol === 'colaborador' ? listarIdeas({ estado: 'borrador' }) : Promise.resolve([])
    const pedirRevisiones =
      rol !== 'admin' && esRevisorElegible ? misRevisiones() : Promise.resolve([])

    Promise.all([pedirBorrador, pedirRevisiones])
      .then(([borradores, revisiones]) => {
        if (cancelado) return
        setDatos({
          borradorPropio: borradores[0] ?? null,
          misPendientesRevisar: revisiones.length,
        })
      })
      .catch(() => {
        if (!cancelado) setDatos(null)
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })

    return () => {
      cancelado = true
    }
  }, [rol, esRevisorElegible])

  return { datos, cargando }
}

function useDatosSistema(
  activo: boolean,
  esAdmin: boolean,
  tiposCabPropios: TipoCAB[],
): { datos: DatosSistema | null; cargando: boolean } {
  const [datos, setDatos] = useState<DatosSistema | null>(null)
  const [cargando, setCargando] = useState(activo)

  useEffect(() => {
    if (!activo) return
    let cancelado = false
    setCargando(true)

    const tiposCabAConsultar: TipoCAB[] = esAdmin ? TODOS_TIPOS_CAB : tiposCabPropios
    const tieneAlgunCab = tiposCabAConsultar.length > 0

    Promise.all([
      listarIdeas(),
      esAdmin ? revisionesSinAsignar() : Promise.resolve(null),
      esAdmin ? misRevisiones() : Promise.resolve(null),
      tieneAlgunCab
        ? Promise.all(tiposCabAConsultar.map((t) => colaComite(t, 'pendiente')))
        : Promise.resolve(null),
      tieneAlgunCab
        ? Promise.all(tiposCabAConsultar.map((t) => colaComite(t, 'aprobada')))
        : Promise.resolve(null),
    ])
      .then(([ideas, sinAsignar, todasPendientesRevision, colasPendientes, colasAprobadas]) => {
        if (cancelado) return

        let pendientesPorPersona: DatosSistema['pendientesPorPersona'] = null
        if (todasPendientesRevision) {
          const porRevisor = new Map<string, RevisionDetalle[]>()
          for (const rev of todasPendientesRevision) {
            const nombre = rev.revisor?.nombre ?? 'Sin asignar'
            porRevisor.set(nombre, [...(porRevisor.get(nombre) ?? []), rev])
          }
          pendientesPorPersona = Array.from(porRevisor.entries())
            .map(([nombre, revs]) => ({
              nombre,
              cantidad: revs.length,
              diasMasAntiguo: Math.max(
                ...revs.map((r) => (r.fecha_asignacion ? diasDesde(r.fecha_asignacion) : 0)),
              ),
            }))
            .sort((a, b) => b.cantidad - a.cantidad)
        }

        setDatos({
          total: ideas.length,
          borrador: ideas.filter((i) => i.estado === 'borrador').length,
          enviada: ideas.filter((i) => i.estado === 'enviada').length,
          sinAsignar: sinAsignar === null ? null : sinAsignar.length,
          enComite: colasPendientes === null ? null : colasPendientes.reduce((acc, c) => acc + c.length, 0),
          aprobadas: colasAprobadas === null ? null : colasAprobadas.reduce((acc, c) => acc + c.length, 0),
          pendientesPorPersona,
        })
      })
      .catch(() => {
        if (!cancelado) setDatos(null)
      })
      .finally(() => {
        if (!cancelado) setCargando(false)
      })

    return () => {
      cancelado = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activo, esAdmin, tiposCabPropios.join(',')])

  return { datos, cargando }
}

export default function PaginaInicio() {
  const usuarioActual = useUsuarioActual()
  const navigate = useNavigate()
  const esAdmin = usuarioActual.rol === 'admin'
  const { veTodasLasIdeas, esRevisorElegible } = useMisPermisos()
  const mostrarDashboardSistema = esAdmin || veTodasLasIdeas

  const { tiposCab } = useEsMiembroCab()
  const { datos: datosPersona } = useDatosPersona(usuarioActual.rol, esRevisorElegible)
  const { datos: datosSistema, cargando: cargandoSistema } = useDatosSistema(
    mostrarDashboardSistema,
    esAdmin,
    tiposCab ?? [],
  )

  const sinNadaEspecial = !mostrarDashboardSistema

  return (
    <div className="page-inicio">
      <div className="inicio-header">
        <div>
          <h1 className="page-title">Hola, {usuarioActual.nombre.split(' ')[0]}</h1>
          <p className="inicio-subtitulo">Portafolio de iniciativas · Grupo ANC</p>
        </div>
        <button className="btn-primary inicio-btn-nueva" onClick={() => navigate('/ideas/nueva')}>
          <FiPlus /> Nueva idea
        </button>
      </div>

      {datosPersona?.borradorPropio && (
        <div
          className="inicio-aviso"
          data-clickable="true"
          onClick={() => navigate(`/ideas/${datosPersona.borradorPropio!.id}`)}
        >
          <FiAlertCircle className="inicio-aviso-icono" />
          <span>
            Tenés 1 idea sin terminar: <strong>{datosPersona.borradorPropio.titulo}</strong> — clic para continuarla
          </span>
        </div>
      )}

      {datosPersona && datosPersona.misPendientesRevisar > 0 && (
        <div className="inicio-aviso" data-clickable="true" onClick={() => navigate('/revision')}>
          <FiUserCheck className="inicio-aviso-icono" />
          <span>
            Tenés <strong>{datosPersona.misPendientesRevisar}</strong> idea
            {datosPersona.misPendientesRevisar === 1 ? '' : 's'} pendiente
            {datosPersona.misPendientesRevisar === 1 ? '' : 's'} de revisar
          </span>
        </div>
      )}

      <div className={`inicio-botones-grandes ${sinNadaEspecial ? '' : 'inicio-botones-discretos'}`}>
        <button className="inicio-boton-grande" onClick={() => navigate('/ideas/nueva')}>
          <FiPlus className="inicio-boton-grande-icono" />
          <span>Registrar nueva idea</span>
        </button>
        <button className="inicio-boton-grande" onClick={() => navigate('/ideas')}>
          <FiFileText className="inicio-boton-grande-icono" />
          <span>Ver mis ideas</span>
        </button>
      </div>

      {mostrarDashboardSistema && (
        <div className="inicio-dashboard">
          {cargandoSistema && <p style={{ color: 'var(--text-muted)' }}>Cargando resumen...</p>}

          {!cargandoSistema && datosSistema && (
            <>
              <div className="inicio-stat-grid">
                <div className="inicio-stat-card" onClick={() => navigate('/admin/ideas')}>
                  <FiClipboard className="inicio-stat-icono" />
                  <div className="inicio-stat-numero">{datosSistema.total}</div>
                  <div className="inicio-stat-label">Total de ideas</div>
                </div>

                {esAdmin && (
                  <div className="inicio-stat-card" onClick={() => navigate('/revision')}>
                    <FiUserCheck className="inicio-stat-icono" />
                    <div className="inicio-stat-numero">{datosSistema.sinAsignar}</div>
                    <div className="inicio-stat-label">Sin asignar</div>
                  </div>
                )}

                {datosSistema.enComite !== null && (
                  <div className="inicio-stat-card" onClick={() => navigate('/comites')}>
                    <FiUsers className="inicio-stat-icono" />
                    <div className="inicio-stat-numero">{datosSistema.enComite}</div>
                    <div className="inicio-stat-label">En comité</div>
                  </div>
                )}

                {datosSistema.aprobadas !== null && (
                  <div className="inicio-stat-card" onClick={() => navigate('/comites')}>
                    <FiCheckCircle className="inicio-stat-icono" />
                    <div className="inicio-stat-numero">{datosSistema.aprobadas}</div>
                    <div className="inicio-stat-label">Aprobadas por comité</div>
                  </div>
                )}
              </div>

              {esAdmin && datosSistema.pendientesPorPersona && datosSistema.pendientesPorPersona.length > 0 && (
                <div className="inicio-pendientes-persona">
                  <h2 className="inicio-seccion-titulo">Pendientes por persona</h2>
                  {datosSistema.pendientesPorPersona.map((p) => (
                    <div key={p.nombre} className="inicio-pendiente-fila">
                      <span className="inicio-pendiente-nombre">{p.nombre}</span>
                      <span className="inicio-pendiente-cantidad">{p.cantidad} idea{p.cantidad === 1 ? '' : 's'}</span>
                      <span className="inicio-pendiente-antiguedad">
                        {p.diasMasAntiguo === 0 ? 'hoy' : `hace ${p.diasMasAntiguo} día${p.diasMasAntiguo === 1 ? '' : 's'}`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

import { useNavigate } from 'react-router-dom'
import { FiAlertCircle } from 'react-icons/fi'
import {
  ACCION_POR_ESTADO,
  ETIQUETA_ESTADO_FLOW,
  PORCENTAJE_POR_ESTADO,
  PROGRESO_POR_ESTADO,
  esEstadoActivo,
} from '../../trazabilidad/estadosFlow'
import type { Idea } from '../types'

/**
 * "Tus ideas en curso" — tarjetas de progreso para el colaborador en la
 * página de inicio.
 *
 * Muestra SOLO las ideas que siguen vivas en el proceso: se ocultan las que
 * llegaron a un estado terminal, sea positivo (documentos_completos) o
 * negativo (revision_rechazada, comite_rechazada). El borrador tampoco
 * aparece acá — la página ya tiene su propio aviso de "idea sin terminar",
 * que lleva a continuar la entrevista en vez de a mirar avance.
 *
 * Es una barra con porcentaje, no el stepper de 5 círculos ni la mini-barra
 * segmentada de "Mis ideas": acá el colaborador quiere una sensación rápida
 * de avance, no el detalle de por qué etapa va. Pero el COLOR sale de
 * PROGRESO_POR_ESTADO, el mismo mapeo que usan los otros dos, así que las
 * tres representaciones no pueden contradecirse.
 */
export default function IdeasEnCurso({ ideas }: { ideas: Idea[] }) {
  const navigate = useNavigate()

  const enCurso = ideas.filter((i) => esEstadoActivo(i.estado_flow))
  // Se oculta la sección entera, no se muestra un "no hay nada": el inicio
  // ya tiene bastante que decir y esto es informativo, no accionable.
  if (enCurso.length === 0) return null

  return (
    <div className="inicio-en-curso">
      <h2 className="inicio-en-curso-titulo">
        Tus ideas en curso
        <span className="inicio-en-curso-conteo">{enCurso.length}</span>
      </h2>

      {enCurso.map((idea) => {
        // esEstadoActivo ya garantizó que no es null.
        const estado = idea.estado_flow!
        const porcentaje = PORCENTAJE_POR_ESTADO[estado]
        const { tipo } = PROGRESO_POR_ESTADO[estado]
        const requiereAccion = tipo === 'accion'

        return (
          <div
            key={idea.id}
            className="inicio-en-curso-card"
            data-clickable="true"
            onClick={() => navigate(`/ideas/${idea.id}`)}
          >
            <div className="inicio-en-curso-fila">
              <span className="inicio-en-curso-nombre">{idea.titulo}</span>
              {requiereAccion && (
                <FiAlertCircle className="inicio-en-curso-alerta" aria-hidden="true" />
              )}
              <span className="inicio-en-curso-porcentaje">{porcentaje}%</span>
            </div>

            <div
              className="inicio-en-curso-barra"
              role="progressbar"
              aria-valuenow={porcentaje}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${idea.titulo}: ${ETIQUETA_ESTADO_FLOW[estado]}`}
            >
              <div
                className={`inicio-en-curso-relleno inicio-en-curso-relleno-${tipo}`}
                style={{ width: `${porcentaje}%` }}
              />
            </div>

            <div className={`inicio-en-curso-estado${requiereAccion ? ' inicio-en-curso-estado-accion' : ''}`}>
              {ETIQUETA_ESTADO_FLOW[estado]}
              {requiereAccion && ACCION_POR_ESTADO[estado] && <> — te toca responder</>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

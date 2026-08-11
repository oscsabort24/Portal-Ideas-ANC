import { FiCircle, FiClock, FiCheckCircle } from 'react-icons/fi'
import type { EstadoBloque, ProgresoBloques } from '../types'

// Etiquetas en lenguaje cotidiano, NO los nombres internos de los bloques:
// esta lista es lo primero que lee alguien que nunca gestionó un proyecto, y
// "Objetivo medible" / "Entregables" / "Alcance" no significan nada para un
// chofer o alguien de bodega. Las claves siguen siendo las de
// core/claude_client.py:ProgresoBloques — solo cambia lo que se muestra.
const BLOQUES: { clave: keyof ProgresoBloques; etiqueta: string }[] = [
  { clave: 'problema_alcance', etiqueta: 'Qué pasa hoy' },
  { clave: 'objetivo_medible', etiqueta: 'Qué mejoraría' },
  { clave: 'beneficios', etiqueta: 'Cuánto se ganaría' },
  { clave: 'entregables', etiqueta: 'Qué te gustaría recibir' },
  { clave: 'riesgos', etiqueta: 'Qué podría complicarse' },
]

const ICONO_BLOQUE: Record<EstadoBloque, JSX.Element> = {
  pendiente: <FiCircle className="checklist-bloque-icono pendiente" />,
  en_progreso: <FiClock className="checklist-bloque-icono en-progreso" />,
  completado: <FiCheckCircle className="checklist-bloque-icono completado" />,
}

export default function ChecklistEntrevista({ progreso }: { progreso: ProgresoBloques | null }) {
  const completados = BLOQUES.filter(({ clave }) => progreso?.[clave] === 'completado').length
  const porcentaje = Math.round((completados / BLOQUES.length) * 100)

  return (
    <aside className="checklist-entrevista" aria-label="Avance de la conversación">
      <div className="checklist-entrevista-titulo">Tu avance</div>

      <div className="checklist-progreso">
        <div
          className="checklist-progreso-barra"
          role="progressbar"
          aria-valuenow={completados}
          aria-valuemin={0}
          aria-valuemax={BLOQUES.length}
          aria-label={`${completados} de ${BLOQUES.length} temas listos`}
        >
          <div className="checklist-progreso-relleno" style={{ width: `${porcentaje}%` }} />
        </div>
        <div className="checklist-progreso-texto">
          {completados} de {BLOQUES.length} temas listos
        </div>
      </div>

      <ul className="checklist-entrevista-lista">
        {BLOQUES.map(({ clave, etiqueta }) => {
          const estado = progreso?.[clave] ?? 'pendiente'
          return (
            <li key={clave} className={`checklist-bloque checklist-bloque--${estado}`}>
              {ICONO_BLOQUE[estado]}
              <span>{etiqueta}</span>
            </li>
          )
        })}
      </ul>

      {/* El guardado automático ya existía (cada turno se persiste como
          borrador), pero nada se lo decía a la persona — y sin saberlo,
          asume que si cierra la pestaña pierde todo. */}
      <p className="checklist-autoguardado">
        Tu avance se guarda solo. Podés cerrar esta página y seguir después desde “Nueva idea”.
      </p>
    </aside>
  )
}

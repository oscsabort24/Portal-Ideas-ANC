import { useEffect, useRef, useState, type ReactNode } from 'react'

// Diagrama de proceso tipo BPMN con carriles (swimlanes), orientación
// vertical: el tiempo corre de arriba hacia abajo, los 4 carriles son
// columnas fijas de izquierda a derecha (Colaborador, IA/Sistema, Revisor
// de área, Comité). Contenido 100% estático — mapeado directamente del
// código real (ideas/router.py, core/claude_client.py, revision/,
// clasificacion/, comites/, documentos/, riesgo/), no es una vista de
// datos reales.
//
// TODAS las conexiones (incluidas las ramas de los rombos y los cruces
// entre carriles) se dibujan como líneas ortogonales (ángulo recto) —
// nunca diagonales ni íconos de flecha sueltos — calculadas en runtime
// midiendo la posición real de cada nodo (mismo mecanismo que se usaba
// antes solo para el loop largo de "cambios solicitados", ahora aplicado
// a todas las conexiones del diagrama para que sea consistente de punta
// a punta).
//
// Simbología: óvalo = inicio/fin, rombo = decisión real, rectángulo =
// paso normal. Único loop de retorno real: "cambios solicitados" (naranja
// punteado) — confirmado con el usuario que "rechazada -> reclasificación"
// NO existe en el código actual (clasificacion/router.py:clasificar
// bloquea reclasificar si el comité ya resolvió, incluso si fue rechazo).

type Columna = 1 | 2 | 3 | 4
type Lado = 'arriba' | 'abajo' | 'izquierda' | 'derecha'

const NOMBRE_CARRIL: Record<Columna, string> = {
  1: 'Colaborador',
  2: 'IA / Sistema',
  3: 'Revisor de área',
  4: 'Comité (CAB)',
}

/** Registro de refs por id de nodo — evita declarar 25 useRef sueltos. */
function useRegistroNodos() {
  const registro = useRef<Record<string, HTMLDivElement | null>>({})
  function refPara(id: string) {
    return (el: HTMLDivElement | null) => {
      registro.current[id] = el
    }
  }
  return { registro, refPara }
}

function Celda({ columna, children }: { columna: Columna; children: ReactNode }) {
  return (
    <div className="flow-bpmn-celda" style={{ gridColumn: columna }}>
      {children}
    </div>
  )
}

function Fila({ children }: { children: ReactNode }) {
  return <div className="flow-bpmn-fila">{children}</div>
}

function NodoRect({
  id,
  refPara,
  etiqueta,
  descripcion,
  admin,
}: {
  id: string
  refPara: (id: string) => (el: HTMLDivElement | null) => void
  etiqueta: string
  descripcion: string
  admin?: boolean
}) {
  return (
    <div className="flow-diagrama-nodo-wrapper">
      <div className="flow-pipeline-nodo flow-bpmn-nodo" ref={refPara(id)}>
        {admin && <span className="flow-bpmn-admin-badge">Admin</span>}
        <div className="flow-diagrama-etiqueta">{etiqueta}</div>
        <div className="flow-diagrama-descripcion">{descripcion}</div>
      </div>
    </div>
  )
}

function NodoOval({
  id,
  refPara,
  etiqueta,
  descripcion,
}: {
  id: string
  refPara: (id: string) => (el: HTMLDivElement | null) => void
  etiqueta: string
  descripcion: string
}) {
  return (
    <div className="flow-diagrama-nodo-wrapper">
      <div className="flow-pipeline-nodo flow-diagrama-nodo--terminal flow-bpmn-nodo" ref={refPara(id)}>
        <div className="flow-diagrama-etiqueta">{etiqueta}</div>
        <div className="flow-diagrama-descripcion">{descripcion}</div>
      </div>
    </div>
  )
}

function NodoRombo({
  id,
  refPara,
  etiqueta,
  descripcion,
}: {
  id: string
  refPara: (id: string) => (el: HTMLDivElement | null) => void
  etiqueta: string
  descripcion: string
}) {
  return (
    <div className="flow-diagrama-nodo-wrapper">
      <div className="flow-diagrama-nodo--decision flow-bpmn-nodo" ref={refPara(id)}>
        <div className="flow-diagrama-rombo-fondo" aria-hidden="true" />
        <div className="flow-diagrama-rombo-texto">{etiqueta}</div>
      </div>
      <div className="flow-diagrama-descripcion">{descripcion}</div>
    </div>
  )
}

interface Conexion {
  desde: string
  hasta: string
  etiqueta?: string
  estilo?: 'normal' | 'naranja'
  saleDesde?: Lado
  entraA?: Lado
  /** Coordenada X absoluta por la que se enruta el tramo vertical central
   * — para loops locales que necesitan rodear un nodo intermedio (ej.
   * "reasignar" tiene que esquivar la fila de "pide resumen" que queda
   * entre el rombo y su destino). */
  viaX?: number
}

// Nota sobre etiquetas: se omiten a propósito en las 4 conexiones "misma
// fila, carriles adyacentes" (entrevista, resumen de revisor, resumen y
// RICE de comité) — el hueco real entre 2 tarjetas de columnas vecinas
// (~50-60px) no alcanza para un texto sin que invada alguna tarjeta. La
// descripción de cada nodo ya explica la interacción; acá alcanza con la
// línea. Las etiquetas de rama (Sí/No/Aprobar/etc.) sí tienen espacio de
// sobra porque viven en el margen entre filas (52px) o en un gutter lateral
// dedicado, nunca pegadas a una tarjeta vecina.
const CONEXIONES: Conexion[] = [
  { desde: 'crearIdea', hasta: 'entrevistaColaborador' },
  { desde: 'entrevistaColaborador', hasta: 'entrevistaIA', saleDesde: 'derecha', entraA: 'izquierda' },
  { desde: 'entrevistaColaborador', hasta: 'generaDocumentos' },
  { desde: 'generaDocumentos', hasta: 'enviaIdea' },
  { desde: 'enviaIdea', hasta: 'calculaRiesgo', etiqueta: 'dispara en paralelo' },
  { desde: 'calculaRiesgo', hasta: 'asignaRevisorAuto' },
  { desde: 'asignaRevisorAuto', hasta: 'rombolHayRevisor' },
  { desde: 'rombolHayRevisor', hasta: 'sinAsignar', etiqueta: 'No' },
  { desde: 'rombolHayRevisor', hasta: 'revisorRecibeIdea', etiqueta: 'Sí' },
  { desde: 'sinAsignar', hasta: 'asignaManualAdmin' },
  // Antes esta conexión iba "hacia atrás" (asignaManualAdmin quedaba en
  // una fila POSTERIOR a revisorRecibeIdea) y su línea terminaba
  // cruzándose con la línea recta que ya baja de revisorRecibeIdea. Se
  // corrigió reordenando las filas más abajo — ahora asignaManualAdmin
  // queda arriba de revisorRecibeIdea, así que esta conexión también
  // fluye hacia abajo como todas las demás.
  { desde: 'asignaManualAdmin', hasta: 'revisorRecibeIdea' },
  { desde: 'revisorRecibeIdea', hasta: 'revisorPideResumen' },
  { desde: 'revisorPideResumen', hasta: 'iaResumenRevision', saleDesde: 'izquierda', entraA: 'derecha' },
  { desde: 'revisorPideResumen', hasta: 'rombolRevisorDecide' },
  // Los 3 loops locales/largos entran SIEMPRE por un lado (izquierda o
  // derecha) porque su último tramo es horizontal — usar 'arriba'/'abajo'
  // ahí (como estaba antes) hacía que la línea terminara flotando al
  // costado del nodo en vez de tocar su borde.
  { desde: 'rombolRevisorDecide', hasta: 'revisorRecibeIdea', etiqueta: 'Reasignar', entraA: 'derecha', viaX: -1 },
  {
    desde: 'rombolRevisorDecide',
    hasta: 'entrevistaColaborador',
    etiqueta: 'Pedir cambios',
    estilo: 'naranja',
    entraA: 'izquierda',
    viaX: -2,
  },
  { desde: 'rombolRevisorDecide', hasta: 'iaClasificaAuto', etiqueta: 'Aprobar' },
  { desde: 'iaClasificaAuto', hasta: 'rombolHayCriterio' },
  { desde: 'rombolHayCriterio', hasta: 'iaPendienteClasificacion', etiqueta: 'No' },
  { desde: 'rombolHayCriterio', hasta: 'comiteEntraCola', etiqueta: 'Sí' },
  { desde: 'iaPendienteClasificacion', hasta: 'clasificaManualAdmin' },
  { desde: 'clasificaManualAdmin', hasta: 'comiteEntraCola' },
  { desde: 'comiteEntraCola', hasta: 'comitePideResumen' },
  { desde: 'comitePideResumen', hasta: 'iaResumenComite', saleDesde: 'izquierda', entraA: 'derecha' },
  { desde: 'comitePideResumen', hasta: 'comiteRice' },
  { desde: 'comiteRice', hasta: 'iaRecalculaRice', saleDesde: 'izquierda', entraA: 'derecha' },
  { desde: 'comiteRice', hasta: 'rombolComiteDecide' },
  { desde: 'rombolComiteDecide', hasta: 'rechazada', etiqueta: 'Rechazar' },
  // "Aprobar" tiene que saltar por encima de "Rechazada" (está en el medio,
  // misma columna) — jog hacia la IZQUIERDA (columna 4 es la última, un
  // jog a la derecha se saldría del diagrama).
  { desde: 'rombolComiteDecide', hasta: 'aprobada', etiqueta: 'Aprobar', entraA: 'izquierda', viaX: -3 },
]

// Códigos especiales de viaX (se resuelven en runtime, relativos a la
// posición real de los nodos involucrados — ver useConexiones):
// -1 = loop local corto (mismo carril, hacia atrás)
// -2 = gutter izquierdo del diagrama (loop largo)
// -3 = gutter local, esquiva un nodo intermedio de la misma columna
const GUTTER_DIAGRAMA = 14
// Mayor al medio-ancho máximo de una tarjeta (240px de max-width → 120px
// desde el centro) más margen — si no, el tramo vertical del jog pasa por
// detrás de la tarjeta vecina en vez de rodearla.
const JOG_LOCAL = 150

function obtenerPunto(rect: DOMRect, contenedor: DOMRect, lado: Lado) {
  const x = rect.left - contenedor.left
  const y = rect.top - contenedor.top
  switch (lado) {
    case 'abajo':
      return { x: x + rect.width / 2, y: y + rect.height }
    case 'arriba':
      return { x: x + rect.width / 2, y }
    case 'izquierda':
      return { x, y: y + rect.height / 2 }
    case 'derecha':
      return { x: x + rect.width, y: y + rect.height / 2 }
  }
}

function calcularPath(p1: { x: number; y: number }, p2: { x: number; y: number }, viaX?: number) {
  if (viaX !== undefined) {
    const path = `M ${p1.x} ${p1.y} L ${viaX} ${p1.y} L ${viaX} ${p2.y} L ${p2.x} ${p2.y}`
    return { path, labelX: viaX, labelY: (p1.y + p2.y) / 2 }
  }
  if (Math.abs(p1.y - p2.y) < 2) {
    // misma fila — línea horizontal directa
    return { path: `M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`, labelX: (p1.x + p2.x) / 2, labelY: p1.y }
  }
  if (Math.abs(p1.x - p2.x) < 2) {
    // mismo carril — línea vertical directa
    return { path: `M ${p1.x} ${p1.y} L ${p2.x} ${p2.y}`, labelX: p1.x, labelY: (p1.y + p2.y) / 2 }
  }
  // cruce de carril — baja, quiebra en horizontal a mitad de camino, baja al destino
  const yMedio = (p1.y + p2.y) / 2
  const path = `M ${p1.x} ${p1.y} L ${p1.x} ${yMedio} L ${p2.x} ${yMedio} L ${p2.x} ${p2.y}`
  return { path, labelX: (p1.x + p2.x) / 2, labelY: yMedio }
}

interface ConexionCalculada extends Conexion {
  path: string
  labelX: number
  labelY: number
}

function useConexiones(
  contenedorRef: React.RefObject<HTMLDivElement>,
  registro: React.MutableRefObject<Record<string, HTMLDivElement | null>>,
) {
  const [calculadas, setCalculadas] = useState<ConexionCalculada[]>([])

  useEffect(() => {
    function recalcular() {
      const contenedor = contenedorRef.current
      if (!contenedor) return
      const rectContenedor = contenedor.getBoundingClientRect()

      const resultado: ConexionCalculada[] = []
      for (const conexion of CONEXIONES) {
        const nodoDesde = registro.current[conexion.desde]
        const nodoHasta = registro.current[conexion.hasta]
        if (!nodoDesde || !nodoHasta) continue

        const rectDesde = nodoDesde.getBoundingClientRect()
        const rectHasta = nodoHasta.getBoundingClientRect()
        const p1 = obtenerPunto(rectDesde, rectContenedor, conexion.saleDesde ?? 'abajo')
        const p2 = obtenerPunto(rectHasta, rectContenedor, conexion.entraA ?? 'arriba')

        let viaX: number | undefined
        if (conexion.viaX === -1) viaX = p1.x + JOG_LOCAL // reasignar: local, hacia la derecha del carril Revisor (col4 está vacía ahí)
        else if (conexion.viaX === -2) viaX = GUTTER_DIAGRAMA // pedir cambios: gutter izquierdo del diagrama
        else if (conexion.viaX === -3) viaX = p1.x - JOG_LOCAL // comité aprobar: local, hacia la izquierda (col4 es la última, col3 está vacía ahí)

        const { path, labelX, labelY } = calcularPath(p1, p2, viaX)
        resultado.push({ ...conexion, path, labelX, labelY })
      }
      setCalculadas(resultado)
    }

    recalcular()
    const observer = new ResizeObserver(recalcular)
    if (contenedorRef.current) observer.observe(contenedorRef.current)
    window.addEventListener('resize', recalcular)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', recalcular)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return calculadas
}

export default function DiagramaFlowControl() {
  const contenedorRef = useRef<HTMLDivElement>(null)
  const { registro, refPara } = useRegistroNodos()
  const conexiones = useConexiones(contenedorRef, registro)

  return (
    <div className="flow-diagrama-wrapper">
      <p className="flow-diagrama-intro">
        Recorrido detallado de una idea, con quién hace qué en cada paso. Óvalo = inicio/fin, rombo = decisión,
        rectángulo = paso normal. Todas las líneas son ortogonales (ángulo recto), incluidas las ramas de los rombos
        y los cruces entre carriles. Único loop de retorno real: "cambios solicitados" (naranja punteado) — una idea
        rechazada por el comité es un final real, no se puede reclasificar ni reabrir.
      </p>

      <div className="flow-bpmn" ref={contenedorRef}>
        <svg className="flow-bpmn-conexiones-svg" aria-hidden="true">
          <defs>
            <marker id="flow-bpmn-flecha" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)" />
            </marker>
            <marker id="flow-bpmn-flecha-normal" viewBox="0 0 10 10" refX="8.5" refY="5" markerWidth="9" markerHeight="9" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-muted)" />
            </marker>
          </defs>
          {conexiones.map((c) => (
            <path
              key={`${c.desde}->${c.hasta}`}
              d={c.path}
              fill="none"
              stroke={c.estilo === 'naranja' ? 'var(--accent)' : 'var(--text-muted)'}
              strokeWidth={c.estilo === 'naranja' ? 2.5 : 2}
              strokeDasharray={c.estilo === 'naranja' ? '6 4' : undefined}
              markerEnd={c.estilo === 'naranja' ? 'url(#flow-bpmn-flecha)' : 'url(#flow-bpmn-flecha-normal)'}
            />
          ))}
        </svg>

        {conexiones
          .filter((c) => c.etiqueta)
          .map((c) => (
            <span
              key={`etiqueta-${c.desde}->${c.hasta}`}
              className={`flow-bpmn-rama-etiqueta-flotante ${c.estilo === 'naranja' ? 'flow-bpmn-rama-etiqueta-flotante--naranja' : ''}`}
              style={{ left: c.labelX, top: c.labelY }}
            >
              {c.etiqueta}
            </span>
          ))}

        <div className="flow-bpmn-header">
          {([1, 2, 3, 4] as Columna[]).map((col) => (
            <div key={col} className="flow-bpmn-header-celda" style={{ gridColumn: col }}>
              {NOMBRE_CARRIL[col]}
            </div>
          ))}
        </div>

        <Fila>
          <Celda columna={1}>
            <NodoOval id="crearIdea" refPara={refPara} etiqueta="Crear idea" descripcion="El colaborador arranca con solo un título." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={1}>
            <NodoRect
              id="entrevistaColaborador"
              refPara={refPara}
              etiqueta="Responde en la entrevista"
              descripcion="Conversa con la IA para documentar problema, objetivo, beneficios, entregables y riesgos."
            />
          </Celda>
          <Celda columna={2}>
            <NodoRect
              id="entrevistaIA"
              refPara={refPara}
              etiqueta="Pregunta y calcula progreso"
              descripcion="Evalúa los 5 bloques en cada turno (progreso_bloques). Nunca decide el cierre."
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={1}>
            <NodoRect
              id="generaDocumentos"
              refPara={refPara}
              etiqueta="Genera o regenera documentos"
              descripcion="Disponible en cualquier momento — se congela apenas la idea llega a comité."
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={1}>
            <NodoRect
              id="enviaIdea"
              refPara={refPara}
              etiqueta="Envía la idea"
              descripcion='Botón "Enviar idea" — el servidor revalida los 5 bloques antes de aceptar.'
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRect id="calculaRiesgo" refPara={refPara} etiqueta="Calcula análisis de riesgo" descripcion="Probabilidad × impacto, categoría automática." />
          </Celda>
        </Fila>
        <Fila>
          <Celda columna={2}>
            <NodoRect
              id="asignaRevisorAuto"
              refPara={refPara}
              etiqueta="Sugiere depto. y asigna revisor"
              descripcion="Sugiere el departamento más afín al contenido de la idea."
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRombo id="rombolHayRevisor" refPara={refPara} etiqueta="¿Hay revisor activo?" descripcion="En el departamento sugerido, o si no, en el del autor." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRect id="sinAsignar" refPara={refPara} etiqueta="Queda sin asignar" descripcion='Revisión "pendiente_asignacion", sin nadie a cargo todavía.' />
          </Celda>
        </Fila>
        <Fila>
          <Celda columna={2}>
            <NodoRect id="asignaManualAdmin" refPara={refPara} etiqueta="Asigna revisor manualmente" descripcion="Elige un encargado de área activo para esta idea." admin />
          </Celda>
        </Fila>

        {/* Punto de convergencia: se llega acá por la rama "Sí" directa
            del rombo de arriba, O por la asignación manual del admin —
            ambos caminos fluyen hacia abajo, sin cruces hacia atrás. */}
        <Fila>
          <Celda columna={3}>
            <NodoRect
              id="revisorRecibeIdea"
              refPara={refPara}
              etiqueta="Recibe la idea asignada"
              descripcion="El revisor de área ve la idea en su cola (automático o manual)."
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={3}>
            <NodoRect id="revisorPideResumen" refPara={refPara} etiqueta="Pide resumen / pregunta a la IA" descripcion="Puede consultar cualquier duda puntual sobre la idea." />
          </Celda>
          <Celda columna={2}>
            <NodoRect
              id="iaResumenRevision"
              refPara={refPara}
              etiqueta="Genera resumen / responde"
              descripcion='Guarda cada pregunta con origen="revision" — el CAB la va a ver después.'
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={3}>
            <NodoRombo id="rombolRevisorDecide" refPara={refPara} etiqueta="Revisor decide" descripcion="Aprobar, pedir cambios, o reasignar a otro revisor." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRect id="iaClasificaAuto" refPara={refPara} etiqueta="Clasifica automáticamente" descripcion="Innovación o Transformación Digital, según el criterio vigente." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRombo id="rombolHayCriterio" refPara={refPara} etiqueta="¿Clasificó con éxito?" descripcion="Necesita un criterio cargado en Criterios IA y que la IA responda." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={2}>
            <NodoRect id="iaPendienteClasificacion" refPara={refPara} etiqueta="Queda pendiente de clasificar" descripcion="Sin criterio cargado, o la IA no pudo procesar la entrevista." />
          </Celda>
          <Celda columna={4}>
            <NodoRect
              id="comiteEntraCola"
              refPara={refPara}
              etiqueta="Idea entra a la cola del comité"
              descripcion="Del tipo CAB correspondiente. Documentos quedan congelados desde acá."
            />
          </Celda>
        </Fila>
        <Fila>
          <Celda columna={2}>
            <NodoRect id="clasificaManualAdmin" refPara={refPara} etiqueta="Clasifica manualmente" descripcion="Elige Innovación o Transformación Digital a mano." admin />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={4}>
            <NodoRect id="comitePideResumen" refPara={refPara} etiqueta="Pide resumen / pregunta a la IA" descripcion="Mismo mecanismo que el revisor." />
          </Celda>
          <Celda columna={2}>
            <NodoRect
              id="iaResumenComite"
              refPara={refPara}
              etiqueta="Responde — incluye lo de revisión"
              descripcion='El resumen ya trae las preguntas con origen="revision".'
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={4}>
            <NodoRect id="comiteRice" refPara={refPara} etiqueta="Completa evaluación RICE" descripcion="Opcional — no bloquea aprobar ni rechazar." />
          </Celda>
          <Celda columna={2}>
            <NodoRect
              id="iaRecalculaRice"
              refPara={refPara}
              etiqueta="Recalcula calificación y prioridad"
              descripcion="Siempre en el servidor. Prioridad forzada a Alta si impacta el plan estratégico."
            />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={4}>
            <NodoRombo id="rombolComiteDecide" refPara={refPara} etiqueta="Comité decide" descripcion="Aprobar o rechazar la idea." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={4}>
            <NodoOval id="rechazada" refPara={refPara} etiqueta="Rechazada" descripcion="Fin real — no se puede reclasificar ni reabrir." />
          </Celda>
        </Fila>

        <Fila>
          <Celda columna={4}>
            <NodoOval
              id="aprobada"
              refPara={refPara}
              etiqueta="Aprobada — proceso completo"
              descripcion="Si no se generaron documentos antes, queda aprobada sin ellos: ya nadie puede generarlos."
            />
          </Celda>
        </Fila>
      </div>
    </div>
  )
}

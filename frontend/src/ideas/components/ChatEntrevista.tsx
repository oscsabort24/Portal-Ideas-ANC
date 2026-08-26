import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import DocumentosGenerados from '../../documentos/components/DocumentosGenerados'
import { enviarIdea, enviarMensaje, obtenerIdea } from '../api'
import type { IdeaDetalle, MensajeEntrevista, ProgresoBloques } from '../types'
import BurbujaMensaje from './BurbujaMensaje'
import ChecklistEntrevista from './ChecklistEntrevista'
import LineaTiempo from './LineaTiempo'
import StepperProgreso from './StepperProgreso'

function claveBorrador(ideaId: number): string {
  return `borrador-mensaje-${ideaId}`
}

// Las opciones sugeridas se acumulan en el campo de texto separadas por
// coma, en vez de enviar el turno al primer toque. Así una pregunta que
// admite varias respuestas ("¿qué te gustaría recibir?") se puede contestar
// con más de una, y la persona todavía puede editar o agregar texto libre
// antes de mandar.
//
// Deliberadamente NO hay un contrato de multi-select con la IA: `options`
// sigue siendo una lista plana de strings (core/claude_client.py). Esto
// cubre el caso sin tocar el prompt ni el Structured Output; el costo es que
// tampoco distingue qué preguntas admiten varias, así que en una de opción
// única nada impide elegir dos. Se asume aceptable: el texto libre siempre
// permitió responder cualquier cosa.
const SEPARADOR_OPCIONES = ', '

function partesDe(texto: string): string[] {
  return texto
    .split(',')
    .map((p) => p.trim())
    .filter(Boolean)
}

function contieneOpcion(texto: string, opcion: string): boolean {
  return partesDe(texto).includes(opcion.trim())
}

// La API real puede tardar hasta ~12s en un turno normal (medido en el
// diagnóstico del bug de tiempos inconsistentes) — 40s da margen de sobra
// sin dejar al usuario esperando indefinidamente si el fetch se cuelga
// (ej. la laptop se suspende, se corta la red a mitad de la espera).
const TIMEOUT_ENVIO_MS = 40_000

function esAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === 'AbortError'
}

// Texto fijo, NO generado por la IA ni persistido en MensajeEntrevista —
// solo se muestra en el frontend mientras la idea no tiene ningún mensaje
// real todavía. En cuanto el usuario envía el primero, deja de renderizarse
// (ver `mensajes.length === 0` donde se usa) y la conversación real empieza.
const MENSAJE_BIENVENIDA =
  '¡Hola! Vamos a conversar un rato sobre tu idea, nada más. Te voy a hacer preguntas cortas, ' +
  'de una en una, y si algo no lo sabés no hay problema — me decís y seguimos. ' +
  'Contame, ¿qué es lo que te gustaría mejorar en tu trabajo?'

// Placeholder que cambia según el tema que la conversación está tocando: da
// una pista concreta de qué tipo de respuesta se espera, en vez del genérico
// "Escribe tu respuesta...". Las claves son las de ProgresoBloques.
const PLACEHOLDER_POR_BLOQUE: Record<keyof ProgresoBloques, string> = {
  problema_alcance: 'Ej. Cada vez que llega una factura tengo que copiarla a mano en el sistema...',
  objetivo_medible: 'Ej. Me ahorraría como dos horas todos los días...',
  beneficios: 'Ej. Hoy me lleva media mañana; con esto sería cuestión de minutos...',
  entregables: 'Ej. Me gustaría que me llegara una alerta al celular...',
  riesgos: 'Ej. Que la gente no lo use, o que el sistema se caiga...',
}

const ORDEN_BLOQUES: (keyof ProgresoBloques)[] = [
  'problema_alcance',
  'objetivo_medible',
  'beneficios',
  'entregables',
  'riesgos',
]

// El primer bloque que no está completado — es el que la IA está indagando
// ahora mismo. Si ya están todos, no hay pista que dar.
function bloqueEnCurso(progreso: ProgresoBloques | null): keyof ProgresoBloques | null {
  if (!progreso) return 'problema_alcance'
  return ORDEN_BLOQUES.find((clave) => progreso[clave] !== 'completado') ?? null
}

export default function ChatEntrevista() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const ideaId = Number(id)

  const [idea, setIdea] = useState<IdeaDetalle | null>(null)
  const [mensajes, setMensajes] = useState<MensajeEntrevista[]>([])
  const [contenido, setContenido] = useState(() => localStorage.getItem(claveBorrador(ideaId)) ?? '')
  const [enviando, setEnviando] = useState(false)
  const [reintentando, setReintentando] = useState(false)
  const [enviandoIdea, setEnviandoIdea] = useState(false)
  // Confirmación de envío. Antes el único acuse era el banner "✓ Idea
  // enviada" dentro del scroll del chat: con una conversación larga la
  // persona podía no verlo nunca, y no ofrecía salida — quedaba en la misma
  // pantalla ya deshabilitada, sin ruta a "Mis ideas".
  const [mostrarConfirmacion, setMostrarConfirmacion] = useState(false)
  // Respuestas sugeridas del último turno. Efímeras a propósito (no vienen
  // en obtenerIdea, ver ideas/schemas.py) — tras recargar la página quedan
  // solo el texto de la pregunta y el campo libre, que es suficiente.
  const [opciones, setOpciones] = useState<string[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cargando, setCargando] = useState(true)
  const finMensajesRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  // Clave de idempotencia del envío en curso. Se genera al primer intento y
  // se CONSERVA mientras ese mensaje no se haya enviado con éxito, para que
  // un reintento manual (típicamente tras el timeout de 40s) reuse el turno
  // que quizá el servidor ya guardó en vez de duplicarlo. Se limpia recién
  // al confirmarse el envío, así el siguiente mensaje estrena clave.
  const idempotencyKeyRef = useRef<string | null>(null)

  // Auto-guarda el texto no enviado — se restaura si la persona recarga la
  // página o vuelve más tarde sin haber presionado enviar.
  useEffect(() => {
    const clave = claveBorrador(ideaId)
    if (contenido.trim()) {
      localStorage.setItem(clave, contenido)
    } else {
      localStorage.removeItem(clave)
    }
  }, [contenido, ideaId])

  useEffect(() => {
    let cancelado = false
    setCargando(true)
    obtenerIdea(ideaId)
      .then((detalle) => {
        if (cancelado) return
        setIdea(detalle)
        setMensajes(detalle.mensajes)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'No se pudo cargar la idea'))
      .finally(() => setCargando(false))
    return () => {
      cancelado = true
    }
  }, [ideaId])

  useEffect(() => {
    finMensajesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [mensajes, enviando])

  // Si se navega a otra idea (o el componente se desmonta) con un envío
  // colgado de la idea anterior, se aborta ese fetch y se resetea
  // `enviando` — así una pestaña vieja nunca queda bloqueada esperando una
  // respuesta que nunca va a aplicar a la idea actual.
  useEffect(() => {
    setEnviando(false)
    // Las opciones sugeridas son del turno de OTRA idea — mostrarlas acá
    // ofrecería respuestas a una pregunta que nunca se hizo.
    setOpciones(null)
    // La clave de idempotencia es de un mensaje concreto de ESTA idea —
    // arrastrarla a otra no tendría sentido (la unicidad es por idea_id).
    idempotencyKeyRef.current = null
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [ideaId])

  // Auto-grow: crece con el contenido (hasta el max-height de #userInput en
  // index.css, de ahí en más scrollea). Se resetea a una línea al vaciarse
  // (después de enviar) o al cargar un borrador guardado. `resize: vertical`
  // en CSS sigue disponible para que el usuario lo agrande más a mano si
  // quiere.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [contenido])

  /** Agrega o saca una opción sugerida del campo de texto, sin enviar.
   *
   * Antes cada botón mandaba el turno al instante, así que solo se podía
   * elegir una. Ahora se acumulan y la persona confirma con el botón de
   * enviar de siempre — el mismo que ya usa para el texto libre. */
  function alternarOpcion(opcion: string) {
    const limpia = opcion.trim()
    setContenido((actual) => {
      const partes = partesDe(actual)
      const siguiente = partes.includes(limpia)
        ? partes.filter((p) => p !== limpia)
        : [...partes, limpia]
      return siguiente.join(SEPARADOR_OPCIONES)
    })
    // El foco vuelve al textarea para que se pueda seguir escribiendo o
    // mandar con Enter sin tener que ir al campo con el mouse.
    textareaRef.current?.focus()
  }

  // Ya no recibe textoDirecto: las opciones sugeridas dejaron de enviar el
  // turno por su cuenta y ahora escriben en el mismo campo, así que este es
  // el único camino de envío y siempre manda el contenido del textarea.
  async function handleEnviar() {
    const texto = contenido.trim()
    if (!texto || enviando || idea?.estado === 'enviada') {
      if (enviando) {
        // Rastro diagnosticable en consola: si esto aparece sin que el
        // usuario haya realmente disparado dos envíos, es la señal de que
        // `enviando` quedó pegado en true por un fetch colgado anterior
        // (justo lo que causó la demo fallida que originó este fix).
        console.warn('[ChatEntrevista] Envío bloqueado: ya hay un envío en curso (enviando=true).')
      }
      return
    }

    if (idempotencyKeyRef.current === null) {
      idempotencyKeyRef.current = crypto.randomUUID()
    }

    setEnviando(true)
    setError(null)
    // Las opciones eran del turno anterior: en cuanto se manda una respuesta
    // dejan de aplicar, aunque la nueva pregunta todavía no haya llegado.
    setOpciones(null)

    // Máximo 2 intentos: el primer timeout dispara UN reintento automático
    // — la Idempotency-Key (ver ideas/api.ts:enviarMensaje) hace esto seguro,
    // reusa el turno ya generado en el servidor en vez de duplicarlo. Solo
    // se reintenta ante AbortError (timeout): un error real de la API
    // (400/500) fallaría exactamente igual al reintentar, así que no vale
    // la pena la espera adicional para el usuario.
    const MAX_INTENTOS = 2
    let respuesta: Awaited<ReturnType<typeof enviarMensaje>> | null = null
    let ultimoError: unknown = null

    for (let intento = 1; intento <= MAX_INTENTOS; intento++) {
      const controller = new AbortController()
      abortControllerRef.current = controller
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_ENVIO_MS)
      try {
        respuesta = await enviarMensaje(ideaId, texto, idempotencyKeyRef.current, controller.signal)
        clearTimeout(timeoutId)
        abortControllerRef.current = null
        break
      } catch (err) {
        clearTimeout(timeoutId)
        abortControllerRef.current = null
        ultimoError = err
        if (!esAbortError(err) || intento === MAX_INTENTOS) break
        setReintentando(true)
      }
    }
    setReintentando(false)

    if (respuesta) {
      setMensajes((prev) => [...prev, respuesta.mensaje_usuario, respuesta.mensaje_asistente])
      setIdea((prev) =>
        prev
          ? {
              ...prev,
              estado: respuesta.idea.estado,
              fecha_envio: respuesta.idea.fecha_envio,
              progreso_bloques: respuesta.idea.progreso_bloques,
            }
          : prev,
      )
      setOpciones(respuesta.opciones)
      // Se limpia siempre: lo que se mandó ES el contenido del textarea,
      // incluidas las opciones que la persona haya ido tocando.
      setContenido('')
      localStorage.removeItem(claveBorrador(ideaId))
      idempotencyKeyRef.current = null
    } else if (esAbortError(ultimoError)) {
      setError('El envío tardó demasiado y se canceló, incluso después de reintentar. Por favor, intentá de nuevo.')
    } else {
      setError(ultimoError instanceof Error ? ultimoError.message : 'No se pudo enviar el mensaje')
    }

    setEnviando(false)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEnviar()
    }
  }

  async function handleEnviarIdea() {
    if (enviandoIdea) return
    setEnviandoIdea(true)
    setError(null)
    try {
      const ideaActualizada = await enviarIdea(ideaId)
      setIdea((prev) => (prev ? { ...prev, ...ideaActualizada } : prev))
      setMostrarConfirmacion(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo enviar la idea')
    } finally {
      setEnviandoIdea(false)
    }
  }

  if (cargando) return <p>Cargando...</p>
  if (!idea) return <p style={{ color: 'var(--error)' }}>{error ?? 'Idea no encontrada'}</p>

  const entrevistaTerminada = idea.estado === 'enviada'
  const bloquesCompletos =
    !!idea.progreso_bloques && Object.values(idea.progreso_bloques).every((estado) => estado === 'completado')

  const claveBloqueEnCurso = bloqueEnCurso(idea.progreso_bloques)
  const placeholder = entrevistaTerminada
    ? 'Esta idea ya fue enviada'
    : claveBloqueEnCurso
      ? PLACEHOLDER_POR_BLOQUE[claveBloqueEnCurso]
      : 'Escribí lo que quieras agregar...'

  return (
    <>
    {/* Arriba de todo: en cuanto la idea sale de borrador, lo primero que
        quiere saber el autor es dónde está y si le toca algo a él. Antes eso
        solo se veía bajando hasta la línea de tiempo, al final de la página. */}
    <StepperProgreso estadoFlow={idea.estado_flow} />

    <div className="chat-entrevista-layout">
      <div className="chat-shell">
        <div className="chat-titulo">{idea.titulo}</div>

        <div className="messages-container">
          {mensajes.length === 0 && (
            <div className="message assistant">
              <div className="msg-bubble">{MENSAJE_BIENVENIDA}</div>
            </div>
          )}
          {mensajes.map((m) => (
            <BurbujaMensaje key={m.id} mensaje={m} />
          ))}
          {enviando && (
            <div className="message assistant">
              {reintentando ? (
                <div className="msg-bubble" aria-label="Reintentando envío...">
                  El envío está tardando más de lo normal — reintentando...
                </div>
              ) : (
                <div className="msg-bubble escribiendo-dots" aria-label="Escribiendo...">
                  <span />
                  <span />
                  <span />
                </div>
              )}
            </div>
          )}
          <div ref={finMensajesRef} />
        </div>

        {entrevistaTerminada && (
          <div className="banner-enviada">✓ Idea enviada — la entrevista quedó registrada.</div>
        )}

        {/* El banner de arriba queda como registro permanente para quien
            vuelva a abrir la idea; este modal es el acuse del momento del
            envío. No se cierra al tocar afuera a propósito: es el unico punto
            del flujo donde se le dice a la persona que hay un historial donde
            seguir el avance. */}
        {mostrarConfirmacion && (
          <div className="confirmacion-overlay" role="dialog" aria-modal="true" aria-labelledby="tituloConfirmacion">
            <div className="confirmacion-modal">
              <div className="confirmacion-icono">✓</div>
              <h2 className="confirmacion-titulo" id="tituloConfirmacion">Idea enviada</h2>
              <p className="confirmacion-texto">
                Podés consultar el progreso en tu historial.
              </p>
              <div className="confirmacion-acciones">
                <button className="btn-primary" onClick={() => navigate('/ideas')}>
                  Ir a Mis ideas
                </button>
                <button className="btn-small" onClick={() => setMostrarConfirmacion(false)}>
                  Seguir acá
                </button>
              </div>
            </div>
          </div>
        )}

        {!entrevistaTerminada && bloquesCompletos && (
          <div className="banner-lista-para-enviar">
            <span>Ya está todo listo. Podés seguir agregando lo que quieras, o mandarla cuando te parezca.</span>
            <button className="btn-primary" onClick={handleEnviarIdea} disabled={enviandoIdea}>
              {enviandoIdea ? 'Enviando...' : 'Enviar idea'}
            </button>
          </div>
        )}

        {error && <p style={{ color: 'var(--error)', fontSize: 13, padding: '0 20px' }}>{error}</p>}

        <div className="input-area">
          {!entrevistaTerminada && !enviando && opciones && opciones.length > 0 && (
            <div className="opciones-rapidas" role="group" aria-label="Respuestas sugeridas">
              {opciones.map((opcion) => (
                <button
                  key={opcion}
                  type="button"
                  className={`opcion-rapida${contieneOpcion(contenido, opcion) ? ' opcion-rapida-elegida' : ''}`}
                  aria-pressed={contieneOpcion(contenido, opcion)}
                  onClick={() => alternarOpcion(opcion)}
                >
                  {opcion}
                </button>
              ))}
            </div>
          )}
          <div className={`input-wrapper ${entrevistaTerminada ? 'disabled' : ''}`}>
            <textarea
              id="userInput"
              ref={textareaRef}
              rows={1}
              placeholder={placeholder}
              value={contenido}
              onChange={(e) => setContenido(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={entrevistaTerminada || enviando}
            />
            <button
              className="btn-send"
              // Envuelto en una lambda a propósito: pasar `handleEnviar`
              // directo le entregaría el MouseEvent como `textoDirecto`.
              onClick={() => handleEnviar()}
              disabled={entrevistaTerminada || enviando || !contenido.trim()}
              aria-label="Enviar mensaje"
            >
              ➤
            </button>
          </div>
        </div>
      </div>

      <ChecklistEntrevista progreso={idea.progreso_bloques} />
    </div>

    <div style={{ marginTop: 20, border: '1px solid var(--border-light)', borderRadius: 'var(--radius)', background: 'var(--surface)' }}>
      <LineaTiempo ideaId={ideaId} />
      <DocumentosGenerados ideaId={ideaId} />
    </div>
    </>
  )
}

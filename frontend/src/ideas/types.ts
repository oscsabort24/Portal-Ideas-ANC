import type { EstadoFlow } from '../trazabilidad/types'

export type EstadoIdea = 'borrador' | 'enviada'
/** 'revisor' = comentario de un revisor de área al pedir cambios. NO es la
 *  IA: se muestra con nombre y estilo propio, y el backend lo excluye del
 *  contexto que le manda al modelo (ver ideas/service.py:historial_para_ia). */
export type RolMensaje = 'usuario' | 'asistente' | 'revisor'
export type EstadoBloque = 'pendiente' | 'en_progreso' | 'completado'

export interface MensajeEntrevista {
  id: number
  rol: RolMensaje
  contenido: string
  orden: number
  creado_en: string
  /** Quién lo escribió, cuando no es el autor ni la IA. Solo viene en los de
   *  rol='revisor'. */
  usuario: { id: number; nombre: string } | null
}

// Mismo orden y claves que core/claude_client.py:ProgresoBloques —
// refleja el estado real que la IA evalúa en cada turno de la entrevista.
export interface ProgresoBloques {
  problema_alcance: EstadoBloque
  objetivo_medible: EstadoBloque
  beneficios: EstadoBloque
  entregables: EstadoBloque
  riesgos: EstadoBloque
}

export interface Idea {
  id: number
  titulo: string
  descripcion: string | null
  estado: EstadoIdea
  autor_id: number
  fecha_creacion: string
  fecha_actualizacion: string
  fecha_envio: string | null
  progreso_bloques: ProgresoBloques | null
  // Estado real del flujo. Solo lo llena el listado (GET /ideas); en el
  // detalle viene null y la línea de tiempo cuenta lo mismo con más contexto.
  // Ver ideas/schemas.py:IdeaOut.estado_flow.
  estado_flow: EstadoFlow | null
}

export interface IdeaDetalle extends Idea {
  mensajes: MensajeEntrevista[]
}

export interface RespuestaEntrevista {
  idea: Idea
  mensaje_usuario: MensajeEntrevista
  mensaje_asistente: MensajeEntrevista
  // Respuestas sugeridas del turno actual, para pintarlas como botones.
  // EFÍMERAS: no se persisten, así que no vuelven tras recargar la página
  // ni vienen en obtenerIdea() — ver ideas/schemas.py:RespuestaEntrevistaOut.
  opciones: string[] | null
}

export type ColorEvento = 'exito' | 'advertencia' | 'peligro' | 'info'

export interface EventoLineaTiempo {
  tipo: string
  descripcion: string
  fecha: string
  color: ColorEvento
}

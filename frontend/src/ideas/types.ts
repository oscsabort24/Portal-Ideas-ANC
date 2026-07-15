export type EstadoIdea = 'borrador' | 'enviada'
export type RolMensaje = 'usuario' | 'asistente'

export interface MensajeEntrevista {
  id: number
  rol: RolMensaje
  contenido: string
  orden: number
  creado_en: string
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
}

export interface IdeaDetalle extends Idea {
  mensajes: MensajeEntrevista[]
}

export interface RespuestaEntrevista {
  idea: Idea
  mensaje_usuario: MensajeEntrevista
  mensaje_asistente: MensajeEntrevista
}

export type ColorEvento = 'exito' | 'advertencia' | 'peligro' | 'info'

export interface EventoLineaTiempo {
  tipo: string
  descripcion: string
  fecha: string
  color: ColorEvento
}

import type { PasoTour } from './pasos'

const AYUDA_POR_RUTA: Record<string, PasoTour> = {
  '/': {
    titulo: 'Inicio',
    texto: 'Tu resumen general: cuántas ideas tenés, cuántas revisiones o ideas de comité están pendientes según tu rol, y accesos rápidos a lo más urgente.',
  },
  '/ideas': {
    titulo: 'Mis ideas',
    texto: 'Acá ves todas las ideas que has creado, con su estado actual (borrador o enviada) y la fecha de cada una.',
  },
  '/ideas/nueva': {
    titulo: 'Nueva idea',
    texto: 'Arrancá con solo un título — no necesitás tener todo resuelto. Al crearla pasás directo a la entrevista con la IA, que te va a ayudar a completar los detalles.',
  },
  '/admin/ideas': {
    titulo: 'Panel de administración',
    texto: 'Vista de solo lectura con todas las ideas del sistema, sin importar quién las creó — para dar seguimiento general al flujo completo.',
  },
  '/flow-control': {
    titulo: 'Flow Control',
    texto: 'Vista de las 10 etapas por las que pasa una idea. La pestaña Matriz cruza departamento × etapa con conteos; la pestaña Visual muestra el pipeline completo con un semáforo de antigüedad por etapa. Hacé click en cualquier celda o nodo para ver el detalle de esas ideas.',
  },
  '/usuarios': {
    titulo: 'Usuarios',
    texto: 'Gestión de las cuentas de las personas: rol, país, compañía, departamento y a quién le reportan.',
  },
  '/departamentos': {
    titulo: 'Departamentos',
    texto: 'Catálogo de departamentos de la organización, usado para asignar personas y para el criterio de "departamentos impactados" de cada idea.',
  },
  '/puestos': {
    titulo: 'Puestos',
    texto: 'Catálogo de puestos por departamento, usado al asignar el puesto de cada persona en Usuarios.',
  },
  '/comite-cab': {
    titulo: 'Miembros del CAB',
    texto: 'Quiénes integran cada comité (CAB de Innovación y de Transformación Digital) — define quién ve la cola de comité y puede aprobar o rechazar ideas ahí.',
  },
  '/criterios': {
    titulo: 'Criterios IA',
    texto: 'Documentos que definen cómo la IA clasifica ideas y asigna revisores. Subir una versión nueva requiere el PIN de administrador.',
  },
  '/revision': {
    titulo: 'Revisión de área',
    texto: 'Las ideas ya enviadas de tu departamento llegan acá. Podés aprobarlas, pedir cambios o reasignarlas a otro encargado de área.',
  },
  '/clasificacion': {
    titulo: 'Ideas por clasificar',
    texto: 'Ideas ya aprobadas en revisión, pendientes de clasificarse como Innovación o Transformación Digital antes de pasar al comité correspondiente.',
  },
  '/comites': {
    titulo: 'Cola del comité (CAB)',
    texto: 'Las ideas clasificadas esperan acá la decisión de tu comité: aprobar, rechazar, completar la evaluación RICE y generar los documentos formales.',
  },
  '/notificaciones': {
    titulo: 'Escalamiento por inactividad',
    texto: 'Configuración de cuánto tiempo puede pasar una idea sin movimiento en cada etapa antes de escalar una notificación, y el historial de lo ya enviado.',
  },
}

const AYUDA_ENTREVISTA: PasoTour = {
  titulo: 'Entrevista con la IA',
  texto: 'Conversá con la IA para documentar tu idea: problema y alcance, objetivo medible, beneficios, entregables y riesgos. El checklist de la derecha muestra qué falta. Cuando los 5 bloques estén completos vas a poder enviarla con el botón "Enviar idea".',
}

const PATRON_IDEA_DETALLE = /^\/ideas\/\d+$/

export function obtenerAyudaPagina(pathname: string): PasoTour | null {
  if (PATRON_IDEA_DETALLE.test(pathname)) return AYUDA_ENTREVISTA
  return AYUDA_POR_RUTA[pathname] ?? null
}

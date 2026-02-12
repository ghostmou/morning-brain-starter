# Addon: Orden de tareas Asana por día de la semana

Fichero externo al skill good-morning. Criterio de ordenación para las tareas que muestra el morning: **prioridad por nombre de proyecto según el día**.

## Clientes por día (contexto)

Reparto de los clientes de `context/clients/` por día de la semana para tenerlo en cuenta en el morning routine (foco, bitácoras, orden de revisión):

| Día       | Cliente       | Notas |
|-----------|---------------|--------|
| **Lunes** | rocinante     | Rocinante Corp |
| **Martes**| mao-kwikowski | Mao-Kwikowski |
| **Miércoles** | mcr       | MCR |
| **Jueves**| tycho         | Tycho |
| **Viernes** | acme         | Acme |

Los nombres coinciden con las carpetas en `context/clients/` y con `config/clients.yaml`. Ajusta el reparto según cómo quieras priorizar clientes cada día.

## Criterio (mismo que en flavors avanzados)

1. **Por día:** Lunes, Martes, … tienen distinta prioridad de proyectos (ver `config/asana_order.yaml`).
2. **Dentro del día:** Las tareas se agrupan por proyecto y se ordenan según la lista del día (primer proyecto = primero en la lista).
3. **Dentro de cada proyecto:** Orden alfabético por nombre de tarea (o por tamaño si usas `[1h]` en el nombre; en la demo se mantiene simple).
4. **Anclas opcionales:** Primera tarea tipo "Buenos días", última "Buenas tardes" si existen en tu lista (el starter no las impone).

## Dónde se configura

- **`config/asana_order.yaml`**: claves `Monday` … `Friday`, cada una con una lista de nombres de proyecto en orden de prioridad. Nombres exactos o subcadenas que coincidan con el nombre del proyecto en Asana.

## Uso en el morning

El script `asana_lite` devuelve las tareas de hoy ya ordenadas según este fichero. Si no existe o el día no está, se muestra orden por defecto (p. ej. alfabético).

La tabla **Clientes por día** sirve para priorizar en el morning qué cliente tiene foco según el día (bitácoras, reuniones, resúmenes); el agente puede consultar este addon para ordenar o destacar la información del cliente del día.

## Ejemplo (demo)

Lunes: Deep Work → Marketing → Management → Personal.  
Viernes: Management → Marketing → Personal → Wrap-up.

Ajusta los nombres en `config/asana_order.yaml` para que coincidan con tus proyectos en Asana.

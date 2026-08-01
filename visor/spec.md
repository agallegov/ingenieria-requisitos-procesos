# Spec: Pedidos del almacén

Proyecto `almacen-de-paco`. Generado desde `planos.json` (la fuente de verdad): no editar a mano.

**Estado del diseño:** listo para revisar · **modo:** entrevista.

**Cobertura observada en el código actual:** no implementado.

## 1. Propósito

La app del almacén de piensos: los pedidos que hoy llegan por WhatsApp y se copian a mano al Excel pasarán a registrarse y facturarse solos. La IA lee el mensaje y monta un borrador, María lo confirma, el código factura y avisa, y el jefe aprueba las excepciones desde el móvil.

Cuando llega un pedido por WhatsApp, María necesita registrarlo y facturarlo sin copiarlo a mano para que el despacho medio baje de 40 a 10 minutos.

Criterios de éxito:
- en un mes, el tiempo medio entre que llega el mensaje y sale el pedido baja de 40 a 10 minutos, y ningún pedido se pierde.

## 2. Actores y vocabulario

- **Paco**: cliente
- **María**: gestiona pedidos
- **el jefe**: aprueba excepciones
- **el almacén**: prepara y envía

- "pedido": lo que un cliente pide de una vez, con sus sacos y su fecha; no es lo mismo que la factura
- "deuda": dinero pendiente de facturas anteriores; con deuda (o con un pedido de más de 1.000€, ver G-1) hace falta visto bueno del jefe

## 3. El proceso (flujos)

La versión gráfica vive en el visor local del paquete (visor/servir.py).

Lo que se construye son los flujos "con la app"; los flujos "hoy" son la foto del antes y se incluyen como contexto.

### El mismo pedido, con la app [con la app · origen: usuario]

El reparto del trabajo: qué queda en personas, qué hace código normal y qué hace un modelo de IA. La IA propone, María confirma: nada se factura sin ojos humanos.

- [persona] Llegó un pedido por WhatsApp · Paco
- [automático: IA] La app leyó el mensaje y montó un borrador de pedido
- ⚠ Excepción: ¿la app entendió el mensaje?
    - si no (audio raro, remitente desconocido, texto ambiguo):
        - [automático: código] Se dejó como pendiente de revisión y se avisó a María por WhatsApp
        - [persona] Lo registró a mano o lo descartó · María
        - …y vuelve al flujo
    - camino normal: sí lo entendió
- [persona] Revisó el borrador y lo confirmó · María
- [automático: código] Se comprobó el stock
- ⚠ Excepción: ¿había stock?
    - si no había:
        - [automático: código] Se avisó a María por WhatsApp
        - [persona] Llamó al proveedor · María
        - …y vuelve al flujo
    - camino normal: sí había
- ⚑ Regla: ¿hacía falta el visto bueno del jefe? (deuda o más de 1.000€)
    - si sí, y el jefe aprobó:
        - [persona] Aprobó desde el móvil · el jefe
        - …y vuelve al flujo
    - si sí, y el jefe rechazó:
        - [persona] Rechazó desde el móvil, escribiendo el motivo · el jefe
        - [automático: código] Se dejó el pedido como anulado y María vio el motivo en su panel
        - aquí termina este camino
    - camino normal: no hacía falta
- [automático: código] Se generó la factura
- [automático: código] Se avisó al almacén por WhatsApp
- [persona] Preparó el pedido y lo marcó como enviado · el almacén

### Un pedido, de la llamada al envío [hoy · origen: usuario]

Cómo funciona el negocio ahora mismo, sin la app.

- [persona] Llegó un pedido por WhatsApp · Paco
- [persona] Lo pasó al Excel · María
- ⚠ Excepción: ¿había stock?
    - si no había:
        - [persona] Llamó al proveedor · María
        - …y vuelve al flujo
    - camino normal: sí había
- [persona] Hizo la factura en Word · María
- ⚑ Regla: ¿hacía falta el visto bueno del jefe?
    - si sí: debía dinero o el pedido pasaba de 1.000€:
        - [persona] Aprobó el pedido · el jefe
        - …y vuelve al flujo
    - camino normal: no hacía falta
- [persona] Preparó y envió el pedido · el almacén

## 4. Recorridos, requisitos y criterios de aceptación

El orden es el orden de entrega. El primero es el esqueleto: recorre el camino feliz de punta a punta.

### REC-1: Esqueleto: un pedido normal, de WhatsApp a enviado (pendiente · 1ª entrega)

Recorrer todo el camino feliz aunque sea en fino: entra el mensaje, María confirma, se factura, el almacén envía.

- **R-1**: Cuando llegue un mensaje de pedido por WhatsApp de un cliente conocido, el sistema deberá montar un borrador de pedido con cliente, líneas y fecha, y guardar el mensaje original. · origen: usuario · código actual: no implementado
  - Evidencia: Proyecto nuevo sin código.
  - Prueba: Pendiente de construcción.
- **R-2**: Cuando María confirme un borrador con stock y sin necesidad de visto bueno (G-1), el sistema deberá generar la factura, apuntar su importe a la cuenta del cliente y avisar al almacén por WhatsApp. · origen: usuario · código actual: no implementado
  - Evidencia: Proyecto nuevo sin código.
  - Prueba: Pendiente de construcción.
- **R-3**: Cuando el almacén responda al aviso marcando el pedido como enviado, el sistema deberá registrar la hora del envío. · origen: usuario · código actual: no implementado
  - Evidencia: Proyecto nuevo sin código.
  - Prueba: Pendiente de construcción.

- **C-1**: Dado que Paco no debe nada y hay 100 sacos de harina en stock / Cuando escribe "40 sacos de harina de 25kg para el jueves" y María confirma el borrador / Entonces se genera la factura, el almacén recibe el aviso por WhatsApp y el pedido queda como facturado
- **C-2**: Dado que llega un audio ininteligible desde un número desconocido / Cuando la app no consigue montar el borrador / Entonces queda como pendiente de revisión, María recibe aviso por WhatsApp y no se factura nada
- **C-6**: Dado un pedido de Paco facturado esta mañana / Cuando el almacén responde LISTO al aviso / Entonces el pedido queda como enviado, con su hora de llegada y su hora de envío guardadas

### REC-2: El visto bueno del jefe: deuda o pedido gordo (pendiente)

Que ningún pedido con deuda o de más de 1.000€ salga sin aprobación (regla G-1).

- **R-4**: Cuando María confirme un borrador de un cliente con deuda pendiente o por importe mayor de 1.000€, el sistema deberá retenerlo y pedir aprobación al jefe por WhatsApp, enseñándole la deuda y el importe. · origen: usuario · código actual: no implementado
  - Evidencia: Proyecto nuevo sin código.
  - Prueba: Pendiente de construcción.
- **R-5**: Cuando el jefe apruebe, el sistema deberá continuar hacia la factura; cuando rechace con motivo, el sistema deberá dejar el pedido como anulado y avisar a María con el motivo. · origen: usuario · código actual: no implementado
  - Evidencia: Proyecto nuevo sin código.
  - Prueba: Pendiente de construcción.

- **C-3**: Dado que Paco debe 300€ / Cuando María confirma su pedido de 40 sacos / Entonces el pedido queda retenido y al jefe le llega la petición con la deuda visible
- **C-4**: Dado que Paco no debe nada / Cuando María confirma un pedido suyo de 60 sacos por 1.200€ / Entonces el pedido queda retenido por pasar de 1.000€
- **C-5**: Dado un pedido retenido de Paco / Cuando el jefe lo rechaza escribiendo el motivo / Entonces el pedido queda anulado y María ve el motivo en su panel

### Episodios reales que sustentan los requisitos

- El 3 de julio Paco pidió 40 sacos debiendo 300€; el pedido esperó 2 horas a que el jefe volviera de la obra y el almacén cerró sin prepararlo. [G-1, R-4]
- En vendimia entraron 52 pedidos en un día y María dejó de contestar el teléfono para poder copiarlos al Excel. [Q-1]

## 5. Reglas de negocio

### G-1: Cuándo necesita un pedido el visto bueno del jefe

| ¿Debe dinero? | ¿Pedido mayor de 1.000€? | Qué pasa |
|---|---|---|
| no | no | sale directo |
| no | sí | aprueba el jefe |
| sí | lo que sea | aprueba el jefe |

## 6. Estados

### pedido

| Estado | Qué se puede hacer (quién, y a qué estado pasa) |
|---|---|
| pendiente de revisión | registrarlo a mano (María) → pasa a 'borrador' · descartarlo (María) → pasa a 'anulado' |
| borrador | editar líneas (María) · confirmar, sin necesidad de visto bueno (María) → pasa a 'facturado' · confirmar, con deuda o más de 1.000€ (María) → pasa a 'retenido' · anular (María) → pasa a 'anulado' |
| retenido | aprobar (el jefe) → pasa a 'facturado' · rechazar con motivo (el jefe) → pasa a 'anulado' |
| facturado | marcar como enviado (el almacén) → pasa a 'enviado' |
| enviado | nada: solo consultar |
| anulado | nada: solo consultar |

## 7. Datos e integraciones

| Cosa | Qué se guarda | De dónde viene |
|---|---|---|
| cliente | nombre, teléfono de WhatsApp, deuda pendiente en euros | se importa del Excel de María |
| pedido | cliente, líneas (producto y cantidad), fecha de entrega, estado, mensaje original de WhatsApp, motivo de rechazo si lo hay, hora de llegada y hora de envío | se empieza de cero |
| producto | nombre, precio, stock del día | lo carga María cada mañana desde su Excel |
| factura | número correlativo, pedido, importe, fecha | la genera la app |

Números del negocio:

| Qué | Cuánto |
|---|---|
| pedidos al día | unos 30, con picos de 50 en vendimia |
| clientes con ficha | unos 200, 40 activos cada semana |

- Habla con **WhatsApp**: recibir pedidos y mandar todos los avisos

## 8. Superficie de uso

### El panel de María

| Campo | Valor |
|---|---|
| Quién entra | María |
| Por dónde llega | ordenador del despacho |
| Cuándo lo usa | cada vez que entra un pedido nuevo o hay un aviso |
| Qué ve nada más entrar | los pedidos de hoy, con los pendientes de revisión y retenidos arriba en naranja |
| Qué puede hacer | confirmar un borrador · corregir un borrador mal leído · registrar un pedido a mano (los de teléfono) · anular un borrador · marcar deuda como pagada |
| Qué NO debe poder jamás | aprobar pedidos retenidos · borrar el historial de un cliente |

### El móvil del jefe

| Campo | Valor |
|---|---|
| Quién entra | el jefe |
| Por dónde llega | móvil, por WhatsApp |
| Cuándo lo usa | solo cuando un pedido queda retenido |
| Qué ve nada más entrar | el pedido, la deuda del cliente, el importe y dos botones: aprobar o rechazar |
| Qué puede hacer | aprobar · rechazar con motivo |
| Qué NO debe poder jamás | editar el pedido · ver otra cosa que los retenidos |

### El WhatsApp del almacén

| Campo | Valor |
|---|---|
| Quién entra | el almacén |
| Por dónde llega | móvil, por WhatsApp |
| Cuándo lo usa | cuando hay un pedido facturado listo para preparar |
| Qué ve nada más entrar | las líneas del pedido y la dirección de entrega |
| Qué puede hacer | marcar como enviado respondiendo LISTO |
| Qué NO debe poder jamás | ver deudas ni precios de los clientes |

### Matriz de permisos

|  | registrar pedido | confirmar borrador | corregir borrador | anular borrador | aprobar retenido | rechazar retenido | marcar deuda pagada | marcar enviado |
|---|---|---|---|---|---|---|---|---|
| María | ✓ | ✓ | ✓ | ✓ |  |  | ✓ |  |
| el jefe |  |  |  |  | ✓ | ✓ |  |  |
| el almacén |  |  |  |  |  |  |  | ✓ |

### Avisos

| Quién se entera | De qué | Por dónde | Cuándo |
|---|---|---|---|
| el almacén | pedido listo para preparar | WhatsApp | al facturarse |
| el jefe | pedido retenido (deuda o más de 1.000€) | WhatsApp | al retenerse |
| María | mensaje que la app no entendió | WhatsApp | al quedar pendiente de revisión |
| María | pedido rechazado por el jefe, con su motivo | el panel | al rechazarse |

### Condiciones de uso

- María registra pedidos con el cliente al teléfono: nada puede tardar más de 5 segundos.
- Si se corta internet media mañana, no se pierde ningún pedido ya registrado.
- La deuda de los clientes solo la ven María y el jefe.

## 9. Calidad y límites

- **Q-1**: Con 30 pedidos en un día, del mensaje de WhatsApp al borrador listo para confirmar pasan menos de 10 segundos.
- **Q-2**: Si la app se cae, al volver no falta ningún pedido ya registrado ni se duplica ninguno.
- **Q-3**: Cada pedido guarda hora de llegada y hora de envío, y el panel enseña el tiempo medio de despacho del mes (así se mide el criterio de éxito).

## 10. Fuera de alcance

- Cobros y pasarela de pago: se sigue cobrando como hasta ahora.
- Control de stock en tiempo real: el stock se comprueba contra la cifra que carga María cada mañana.

## 11. Preguntas abiertas

Buzón del constructor: sus dudas se apuntan aquí, nunca se responden de palabra.

- (Ninguna por ahora.)


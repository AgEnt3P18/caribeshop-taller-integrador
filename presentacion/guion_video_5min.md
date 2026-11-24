# Guion del video — CaribeShop en Azure

## 1. Portada — Santiago

Hola a todos. Somos Santiago Payares y Cristian Benítez, y hoy les vamos a mostrar nuestro taller integrador de Infraestructura para TI.

Construimos en Azure la plataforma de una tienda en línea, CaribeShop: segura, que crezca sola cuando llega mucha gente y que siga funcionando aunque algo falle.

## 2. El reto — Santiago

Para ponernos en contexto: CaribeShop es una tienda de Cartagena que el año pasado la pasó mal.

Primero se cayó en plena promoción, porque no aguantó tantas visitas. Después se volvió a caer, porque todo dependía de una sola máquina. Y para rematar, una auditoría encontró la contraseña de la base de datos dentro del código y el acceso remoto abierto a cualquiera en Internet.

Entonces nos propusimos tres cosas: que la plataforma escale sola, que sobreviva a las fallas y que cierre esos huecos de seguridad.

## 3. Arquitectura — Cristian

Les cuento cómo quedó por dentro.

Todo lo creamos con código, usando Terraform. No hicimos nada a mano en el portal.

Las visitas llegan a una dirección pública y pasan por un balanceador de carga, que cada cinco segundos le pregunta a cada servidor si está bien. Detrás hay un grupo de máquinas repartidas en tres zonas distintas: mínimo dos y máximo cuatro, que se agregan o se quitan solas según la carga.

Ninguna de esas máquinas tiene una IP pública, y la red solo deja pasar el tráfico web. La contraseña ya no está en el código: vive en un Key Vault, y la aplicación la consulta con su propia identidad. Y todo queda registrado, con alertas al correo.

## 4. Seguridad y DevSecOps — Cristian

Configurar la seguridad no era suficiente: queríamos comprobarla, así que intentamos romperla.

Tratamos de leer la contraseña desde otra red, con un usuario que sí tenía permisos, y el firewall lo bloqueó. Las máquinas solo pueden leer un único secreto, y la aplicación nunca lo muestra. Desde adentro de un servidor intentamos salir a Internet, y tampoco se pudo.

Además, cada cambio en el código pasa por una revisión automática. Cuando propusimos a propósito un cambio que dejaba el acceso remoto expuesto, el sistema lo bloqueó.

## 5. Demo en vivo — Santiago

*Reproducir el video al empezar a hablar.*

Vamos con la demostración en vivo.

Aquí está la tienda funcionando, y vemos cómo consulta su contraseña sin mostrarla nunca.

Ahora lanzamos una prueba de carga: doscientos sesenta usuarios entrando al mismo tiempo. El procesador pasa del setenta por ciento, y la plataforma espera unos minutos para confirmar que la carga es real. Esa espera la adelantamos en el video.

Y miren: aparece una máquina nueva, en otra zona, sin que nadie la haya creado.

Ahora provocamos una falla a propósito: borramos uno de los servidores mientras la gente sigue comprando. Hay unos segundos de errores, justo lo que tarda el balanceador en darse cuenta, y enseguida deja de mandarle tráfico.

Y la tienda sigue en línea con los servidores que quedan, sin que tuviéramos que tocar nada.

## 6. Resultados medidos — Cristian

Y estos son los números.

Primero medimos cuánto aguanta una sola máquina: unas ciento veinte peticiones por segundo antes de empezar a ponerse lenta.

En una prueba de treinta y cinco minutos, subiendo y bajando la carga, la plataforma pasó de dos a cuatro máquinas y volvió a dos, con apenas medio por ciento de errores.

En las pruebas de falla, cuando un servidor deja de estar sano, sale del balanceador en unos ocho segundos sin que nadie lo note. Y cuando lo borramos de golpe, la capacidad se recupera en menos de dos minutos.

Y aprendimos que el escalado automático tarda unos cinco minutos en reaccionar, así que para una campaña conviene programarlo con anticipación.

## 7. Conclusiones — Santiago

Para cerrar.

La plataforma tiene una disponibilidad estimada del noventa y nueve coma noventa y siete por ciento. Cuesta alrededor de ciento setenta y cuatro dólares al mes, y gracias al escalado automático ahorra cerca de un treinta y siete por ciento frente a dejar todas las máquinas encendidas siempre.

Todo quedó como código, y al terminar eliminamos los recursos.

Como siguiente paso proponemos escalar de forma predictiva y replicar todo en una segunda región.

Muchas gracias.

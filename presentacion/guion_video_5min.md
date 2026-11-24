# Guion del video — CaribeShop en Azure (5 minutos)

Integrantes: Santiago Payares González · Cristian Matteo Benitez Montes.
Formato: llamada grupal en Teams, grabada y compartiendo pantalla con `CaribeShop_video_5min.pptx` en modo presentación.

| Tiempo | Diapositiva | Habla |
|---|---|---|
| 0:00 – 0:15 | 1 · Portada | Santiago |
| 0:15 – 0:40 | 2 · El reto | Santiago |
| 0:40 – 1:25 | 3 · Arquitectura | Cristian |
| 1:25 – 2:10 | 4 · Seguridad y DevSecOps | Cristian |
| 2:10 – 3:30 | 5 · Demo en vivo (reproducir el video de 78 s) | Santiago (narra sobre el video) |
| 3:30 – 4:25 | 6 · Resultados medidos | Cristian |
| 4:25 – 5:00 | 7 · Conclusiones | Santiago |

## Texto por diapositiva

### 0:00 – 0:15 · 1 · Portada — Santiago

Hola, somos Santiago Payares y Cristian Benítez. Les presentamos nuestro taller integrador de Infraestructura para TI: la plataforma de CaribeShop en Azure, segura, escalable y altamente disponible, desplegada completamente como código.

### 0:15 – 0:40 · 2 · El reto — Santiago

CaribeShop es una tienda en línea de Cartagena que el año pasado tuvo tres problemas: se cayó por saturación durante una promoción, se cayó otra vez porque tenía una sola máquina virtual, y una auditoría encontró la contraseña de la base de datos en el repositorio y el puerto SSH abierto a Internet. Nuestro objetivo fue resolver los tres: escalar solo, seguir en línea ante fallas y cerrar los huecos de seguridad.

### 0:40 – 1:25 · 3 · Arquitectura — Cristian

Esta es la arquitectura. Todo se creó con Terraform: 33 recursos en un solo apply, con el estado guardado en una cuenta de almacenamiento remota y nunca en Git. El tráfico entra por una IP pública zonal-redundante a un Load Balancer Standard que revisa la salud de cada instancia en la ruta /health cada 5 segundos. Detrás hay un VM Scale Set repartido en las tres zonas de disponibilidad de East US, con mínimo 2 y máximo 4 instancias, sin IPs públicas y con reparación automática. La subred solo deja entrar el puerto 80 y solo deja salir hacia Key Vault, Monitor y Storage. La aplicación lee su secreto desde Key Vault con una identidad administrada, y todo queda auditado en Log Analytics con alertas por correo.

### 1:25 – 2:10 · 4 · Seguridad y DevSecOps — Cristian

No nos quedamos en configurar la seguridad: intentamos romperla. Desde Cloud Shell, con un usuario que sí tiene el rol, leer el secreto falla por el firewall del Key Vault. La identidad de las máquinas solo puede leer un único secreto, y la app solo muestra su hash. Desde dentro de una VM no se puede salir a Internet. Y Azure Policy rechaza crear una tarjeta de red con IP pública o recursos fuera de East US. Además, cada pull request pasa por GitHub Actions: formato, validación y Checkov bloqueante. Un PR que abría SSH a Internet fue rechazado automáticamente, y su corrección pasó en verde.

### 2:10 – 3:30 · 5 · Demo en vivo (reproducir el video de 78 s) — Santiago (narra sobre el video)

Ahora la demostración en vivo. [0:00] Primero la tienda responde a través del balanceador y lee su secreto de Key Vault sin mostrar su valor. [0:13] Lanzamos Locust con 260 usuarios concurrentes; la CPU supera el 70 por ciento y el autoscale empieza a contar su ventana de 5 minutos, que aquí aceleramos. [0:36] Aparece una tercera instancia en otra zona: el scale-out ocurrió solo. [0:43] Ahora provocamos una falla abrupta: eliminamos una instancia con la carga activa. La sonda de salud la saca del balanceador en unos 10 segundos y solo vemos una ráfaga corta de errores. [1:08] La tienda sigue en línea con las instancias restantes, sin intervención manual.

### 3:30 – 4:25 · 6 · Resultados medidos — Cristian

Estos son los números. Primero medimos la capacidad de una sola instancia: 119 peticiones por segundo antes de que el percentil 95 supere un segundo. Con una prueba escalonada de 35 minutos, el autoscale pasó de 2 a 4 instancias y volvió a 2, con apenas 0,55 por ciento de error. En las pruebas de falla, una instancia marcada como no sana salió del balanceador en 8,2 segundos sin errores adicionales, y al eliminar una instancia de golpe la capacidad mínima se recuperó en 109 segundos. La lección: el autoscale tarda unos 5 minutos en reaccionar, así que para la campaña recomendamos un perfil programado o autoscale predictivo.

### 4:25 – 5:00 · 7 · Conclusiones — Santiago

En conclusión: la arquitectura tiene un SLA compuesto estimado de 99,97 por ciento, cuesta unos 174 dólares al mes con dos instancias y el autoscale ahorra un 37 por ciento frente a dimensionar fijo para el pico. Todo está en Terraform, sin pasos manuales, y los recursos se destruyeron al terminar. Como siguientes pasos proponemos autoscale predictivo, Application Gateway con WAF y TLS, y una segunda región. Gracias.

## Indicaciones

- **Diapositiva 5:** al llegar, hacer clic en el video para reproducirlo (dura 78 s) y narrar encima siguiendo las marcas de tiempo [0:00], [0:13], [0:36], [0:43] y [1:08], que también están en la diapositiva.
- **Tiempo:** ritmo tranquilo de ~150 palabras/min. Si van largos, recorten la diapositiva 3 (arquitectura), no la demo.
- **Participación:** los dos integrantes deben verse o escucharse en la grabación de Teams (requisito del taller).
- Total del guion: ~623 palabras.

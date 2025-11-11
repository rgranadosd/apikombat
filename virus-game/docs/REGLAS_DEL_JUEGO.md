# Reglas completas del juego – API Kombat

## Objetivo del juego

Ser el primer jugador en colocar **4 aspectos saludables** en su tablero. Un aspecto está saludable cuando **no es vulnerable**.

## Componentes del juego

### Jugadores

- 2 jugadores: `Tú` vs `IA`.
- Cada jugador dispone de:
  - Una mano de cartas (sin límite, aunque al finalizar el turno se vuelve a 3 cartas).
  - Un tablero con 4 espacios de aspecto.
  - Un escudo de **Code Freeze** (se activa con una carta especial).

### Mazo de cartas (89)

1. **Aspectos (Scoring)** – 17 cartas  
   - 4 copias de cada color: Seguridad, Documentación, Gobierno y Performance.  
   - 1 carta multicolor (*Wildcard*).

2. **Ataques y Problemas** – 29 cartas  
   - 16 cartas de ataque de Seguridad (4× DoS, SQL Injection, OWASP, Brute-Force).  
   - 12 cartas de Problema (4× Documentación, Gobierno, Performance).  
   - 1 carta multicolor (Ataque/Problema).

3. **Protecciones** – 29 cartas  
   - 16 cartas de protección de Seguridad (4× OAuth2/JWT, HTTPS/SSL, Validación de Entrada, Rate Limiting).  
   - 12 cartas de protección genérica (4× Documentación, Gobierno, Performance).  
   - 1 carta multicolor (Protección).

4. **Intervenciones** – 14 cartas  
   - 4× Refactoring, 4× Migración, 4× Activo-Activo.  
   - 1× Code Freeze, 1× Rollback.

## Estados de los aspectos

1. **Vulnerable**  
   - Un ataque destruye el aspecto si vuelve a impactar.  
   - Visible mediante marcadores de alerta.

2. **Protecciones** (`0-2`)  
   - **0**: sin protección.  
   - **1**: protegido (bloquea ataques).  
   - **2**: fortalecido (bloquea ataques y no puede sufrir Activo-Activo).

## Tipos de cartas y efectos

### Aspectos (`aspecto` / `scoring`)
- Coloca un nuevo aspecto en tu tablero.
- No puedes duplicar color ni superar los 4 aspectos.
- Las cartas multicolor adopta el primer color disponible.
- Siempre entran saludables (no vulnerables, 0 protecciones).

### Ataques y Problemas (`ataque`, `problema`, `virus`)
- Se dirigen al tablero rival.
- Code Freeze bloquea el ataque y se consume.
- Las protecciones ≥1 impiden el efecto.
- Si el aspecto objetivo está saludable → pasa a vulnerable.  
  Si ya está vulnerable → se destruye.

### Protecciones (`proteccion`, `medicina`)
- Objetivo: tus propios aspectos.
- Si está vulnerable, primero lo cura.
- Incrementa protección hasta un máximo de 2.

### Intervenciones (`intervencion`, `tratamiento`)

**Migración (ladrón/migracion)**  
Roba un aspecto que el rival tenga y tú no. Mantiene vulnerabilidad y protecciones. Code Freeze lo bloquea.  
Restricciones: el rival debe poseer un aspecto que te falte y, si apuntas a un color específico, debe existir.

**Refactoring (trasplante/refactoring)**  
Intercambia un aspecto tuyo con uno rival. Puede apuntar a un color concreto. Mantiene estados. Code Freeze lo bloquea.  
Requiere que ambos tengan al menos un aspecto.

**Activo-Activo (activo_activo/contagio)**  
Vulnera un aspecto rival que coincida con uno tuyo vulnerable. No funciona si el objetivo está fortalecido o ya vulnerable. Code Freeze lo bloquea.

**Code Freeze (code_freeze/guante)**  
Activa un escudo que bloquea el próximo ataque/intervención que realmente te afectaría. El escudo se consume al bloquear.

**Rollback (rollback/error)**  
Reduce en 1 la protección de un aspecto rival. Code Freeze lo bloquea. Debe existir un objetivo con protección ≥1.

## Flujo del juego

1. **Preparación**: se baraja el mazo, se reparten 3 cartas a cada jugador y se decide quién inicia.  
2. **Turno** – el jugador elige:
   - **Jugar una carta** (si es válida, aplica el efecto y pasa el turno).  
   - **Descartar** una o varias cartas (pasa el turno).  
   - **Pasar** (si no puede o no quiere jugar/descartar).  
3. **Fin del turno**: roba hasta tener 3 cartas. Si el mazo se agota, recicla el descarte.  
4. **Verificación de victoria**: si algún jugador tiene 4 aspectos saludables, gana inmediatamente.

## Cartas multicolor (Wildcards)

- **Aspectos**: toman el primer color que no tengas.  
- **Ataques/Problemas**: buscan el primer aspecto rival sin protección.  
- **Protecciones**: se asignan al primer aspecto disponible del jugador.

## Reciclaje del descarte

Cuando el mazo se queda sin cartas:
1. Baraja todo el descarte.
2. Ese mazo reciclado pasa a ser el nuevo mazo principal.

## Estados especiales

### Code Freeze
- Se activa con la carta homónima.
- Bloquea el siguiente ataque/intervención que te afecte.
- Se consume tras bloquear.

### Protecciones
- 1: protege frente a ataques.  
- 2: protege y evita efectos de Activo-Activo.  
- Nunca superan el nivel 2.

### Vulnerabilidad
- Un ataque posterior destruye el aspecto.
- Puede eliminarse aplicando protección.

## Condiciones de victoria

### Victoria
- Al alcanzar 4 aspectos saludables.  
- Si ambos llegan simultáneamente, gana quien lo logró primero.

### Empate / Bloqueo
- Tras 50 turnos sin jugadas válidas, la partida se declara bloqueada.

## Restricciones generales

1. **Límite de aspectos**: máximo 4 y únicos por color.  
2. **Mano**: sin límite superior; al final del turno vuelve a 3 cartas si hay mazo.  
3. **Validación**: las cartas solo se juegan si cumplen sus condiciones.  
4. **Orden de efectos**: se resuelven al instante; si fallan, la carta ya ha sido jugada.

## Notas técnicas

- Turnos alternos humanos/IA.
- Siempre hay opción de jugar, descartar o pasar.
- El descarte se recicla automáticamente.
- La verificación de victoria ocurre tras cada acción.
- Los efectos son atómicos: o se aplican completamente, o no se aplican.

---

**Fin de las reglas.**


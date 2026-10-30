import asyncio # librería estándar de Python para manejar tareas asíncronas (varias cosas al mismo tiempo sin bloquear el programa).
import websockets # permite crear un servidor WebSocket en Python (para recibir mensajes desde HTML/JS en tiempo real).
import socket # librería de bajo nivel para abrir una conexión TCP al robot UR y enviarle los comandos URScript.
import rtde_receive # libreria para leer posiciones del robot.
import math

# -----------------------
# Configuración del robot
# -----------------------
# ROBOT_IP = "192.168.0.158"   # IP de URSim
ROBOT_IP = "157.253.197.179"   # IP Robot Real
SOCKET_PORT = 30002         # Puerto 30002 → es la script interface, donde puedes mandar comandos en texto (speedj, stopj, etc.).
UR_PORT_RTDE = 30004     # Puerto de RTDE

"""Conexión vía socket para enviar scripts"""
try:
    r_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #abre un socket TCP hacia el robot (o simulador URSim).
    r_socket.connect((ROBOT_IP, SOCKET_PORT)) 
    print(f"[UR] Conectado a Robot(Socket) - Envio: {ROBOT_IP}:{SOCKET_PORT}")
except Exception as e:
    print(f"[UR] Error conectando a UR(Socket) - Envio: {e}")
    raise
# 👉 Desde este punto en adelante, el socket ur_sock está abierto y puedes enviarle strings como "speedj([0.5,0,0,0,0,0], 1.0, 0.1)\n".

# Clientes conectados
connected_clients = set()

# Define los límites de cada articulación (en radianes)
JOINT_LIMITS = {
  0: (math.radians(-340), math.radians(340)),  # J1
  1: (math.radians(-120), math.radians(-40)),  # J2 entre -120° y -40°
  2: (math.radians(-80), math.radians(80)),  # J3 entre -80° y 80°
  3: (math.radians(-300), math.radians(300)), # ✅ J4 (muñeca 1) entre -300° y +300°
  4: (math.radians(-300), math.radians(300)), # ✅ J5 (muñeca 2) entre -300° y +300°
  5: (math.radians(-200), math.radians(200)), # ✅ J6 (muñeca 3) entre -200° y +200°
}
SAFE_MARGIN = math.radians(10)  # asegura que se detenga antes de llegar al límite físico. 10 grados → 0.174 rad

HOME_JOINTS = [
    1.00805,    # J1: 57.76°
    -1.570796,  # J2: -90°
    1.570796,   # J3: 90°
    -1.570796,  # J4: -90°
    -1.570796,  # J5: -90°
    0.0         # J6: 0°
]

HOME_POINT_CMD = (
    f"movej({HOME_JOINTS}, a=0.3, v=0.15)\n"
) # Posición home del robot

#Movimiento lineal
CARTESIAN_SPEED = 0.02  # 2 cm/s, inicialmente en URSim
CARTESIAN_ACCEL = 0.1   # m/s²
CARTESIAN_TIME = 0.1    # segundos por instrucción



CARTESIAN_VELOCITY = {
    # Eje Z - Vertical
    "arriba":    [0, 0, CARTESIAN_SPEED, 0, 0, 0],
    "abajo":     [0, 0, -CARTESIAN_SPEED, 0, 0, 0],

    # Eje X - Adelante / Atrás
    "adelante":  [CARTESIAN_SPEED, 0, 0, 0, 0, 0],
    "atras":     [-CARTESIAN_SPEED, 0, 0, 0, 0, 0],

    # Eje Y - Izquierda / Derecha
    "izquierda": [0, CARTESIAN_SPEED, 0, 0, 0, 0],
    "derecha":   [0, -CARTESIAN_SPEED, 0, 0, 0, 0],
}



# Límites cartesianos del TCP
# -----------------------------------
# Límites verticales del TCP - URSim
# -----------------------------------
Z_HOME = 0.3127495509466381
# Recorrido permitido: +/- 5 cm
Z_MIN = Z_HOME - 0.13
Z_MAX = Z_HOME + 0.10
# Margen experimental de frenado
Z_MARGIN = 0.01


# -----------------------------------
# Límites del TCP en eje X - URSim
# -----------------------------------
X_HOME = -0.0646679620808724
X_MIN = X_HOME - 0.8
X_MAX = X_HOME + 0.8
X_MARGIN = 0.01


# -----------------------------------
# Límites cartesianos del eje Y
# -----------------------------------
Y_HOME = -0.31207534402369824
Y_MIN = Y_HOME - 0.10
Y_MAX = Y_HOME + 0.10
Y_MARGIN = 0.01


# Desaceleración cartesiana para URSim
STOPL_ACCEL = 0.1

print(f"[TCP] HOME: {Z_HOME:.4f} m")
print(f"[TCP] Z mínima: {Z_MIN:.4f} m")
print(f"[TCP] Z máxima: {Z_MAX:.4f} m")


# Conexión con rtde para leer datos del robot
"""Conexión vía RTDE para recibir estado"""
try:
    rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)
    print(f"[RTDE] Conectado a Robot(RTDE) {ROBOT_IP}:{UR_PORT_RTDE}")
except Exception as e:
    print(f"[RTDE] Error conectando Robot(RTDE): {e}")
    raise


# Estado global (compartido)
current_cmd = None  # guarda el comando actual. "base_izquierda", "base_derecha" o None
last_position = None   # última posición TCP o joints

# manejar clientes WebSocket
async def handle_client(websocket, path=None):  # <-- path es opcional
  """Recibe mensajes WebSocket y se cambia el estado current_cmd."""
  global current_cmd
  client = websocket.remote_address
  print(f"[WS] Cliente conectado: {client}, path={path}")
  connected_clients.add(websocket)   # ➕ Guardamos al cliente

  try:
    async for message in websocket: #escucha mensajes en tiempo real.
      print(f"[WS] Mensaje recibido: {message}")
      if message == "base_izquierda":
        current_cmd = "base_izquierda"
      elif message == "base_derecha":
        current_cmd = "base_derecha"
      elif message == "hombro_izquierda":
        current_cmd = "hombro_izquierda"
      elif message == "hombro_derecha":
        current_cmd = "hombro_derecha"
      elif message == "codo_izquierda":
        current_cmd = "codo_izquierda"
      elif message == "codo_derecha":
        current_cmd = "codo_derecha"
      elif message == "muneca1_izquierda":
        current_cmd = "muneca1_izquierda"
      elif message == "muneca1_derecha":
        current_cmd = "muneca1_derecha"
      elif message == "muneca2_izquierda":
        current_cmd = "muneca2_izquierda"
      elif message == "muneca2_derecha":
        current_cmd = "muneca2_derecha"
      elif message == "muneca3_izquierda":
        current_cmd = "muneca3_izquierda"
      elif message == "muneca3_derecha":
        current_cmd = "muneca3_derecha"
      elif message in CARTESIAN_VELOCITY:
        current_cmd = message
        print(f"[UR] Movimiento cartesiano: {message}")

      #movimiento lineal
      elif message == "stop":
          previous_cmd = current_cmd
          current_cmd = None

          try:
              if previous_cmd in CARTESIAN_VELOCITY:
                  r_socket.sendall(b"stopl(0.1)\n")
                  print("[UR] STOP CARTESIANO enviado")
              else:
                  r_socket.sendall(b"stopj(1.0)\n")
                  print("[UR] STOP ARTICULAR enviado")

          except Exception as e:
              print("[UR] Error enviando STOP:", e)
              raise

      #Movimiento articular
      # elif message == "stop":
      #     current_cmd = None
      #     try:
      #         r_socket.sendall(b"stopj(1.0)\n")
      #         print("[UR] STOP enviado")
      #     except Exception as e:
      #         print("[UR] Error enviando STOP:", e)
      #         raise

      elif message == "home":
          current_cmd = None
          print("[UR] HOME solicitado")

          try:
              r_socket.sendall(HOME_POINT_CMD.encode("utf-8"))
              print("[UR] Movimiento HOME enviado")
          except Exception as e:
              print("[UR] Error enviando HOME:", e)

      else:
        print("[WS] Comando no reconocido:", message)

  except websockets.exceptions.ConnectionClosedOK:
    print("[WS] Cliente desconectado (OK)")
  except Exception as e:
    print("[WS] Excepción en handler:", e)
  finally:
    # Si el cliente que desconectó era el que dejó el comando activo,
    # podrías decidir poner current_cmd = None aquí si quieres seguridad.
    print(f"[WS] Conexión finalizada: {client}")

# Función para enviar mensajes a todos los clientes conectados
async def notify_clients(message: str):
  """Envía un mensaje a todos los clientes WebSocket conectados."""
  if connected_clients:  # Solo si hay clientes
    await asyncio.gather(*[ws.send(message) for ws in connected_clients])


# Es un bucle infinito que cada 8 ms (≈125 Hz) revisa current_cmd y, si hay un movimiento activo, envía continuamente el comando speedj(...) al robot.
async def motion_loop():
  """Envía speedj repetidamente mientras current_cmd no sea None,
    con chequeo de límites en RTDE."""
  global current_cmd
  while True:
    try:
      # Leer posiciones articulares actuales
      joints = rtde_r.getActualQ()  # devuelve lista de 6 floats - joins (radianes)

      if current_cmd == "base_izquierda":
        # Controlando solo la articulación 0
        limit = JOINT_LIMITS[0][0]  # límite inferior J0
        if joints[0] <= limit + SAFE_MARGIN:
          print("[SAFETY] Límite cercano en J0 (izquierda). Parando.")
          r_socket.send(b"stopj(1.0)\n")
          current_cmd = None
          await notify_clients("limit_reached")  # 🔔 Notificar
        else:
          cmd = "speedj([-0.5,0,0,0,0,0], 1.0, 0.1)\n"
          r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "base_derecha":
        limit = JOINT_LIMITS[0][1]  # límite superior J0
        if joints[0] >= limit - SAFE_MARGIN:
          print("[SAFETY] Límite cercano en J0 (derecha). Parando.")
          r_socket.send(b"stopj(1.0)\n")
          current_cmd = None
          await notify_clients("limit_reached")  # 🔔 Notificar
        else:
          cmd = "speedj([0.5,0,0,0,0,0], 0.5, 0.1)\n"
          r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "hombro_izquierda":
        limit = JOINT_LIMITS[1][0]  # límite superior J1
        if joints[1] <= limit + SAFE_MARGIN:
          print("[SAFETY] Límite cercano en J1 (derecha). Parando.")
          r_socket.send(b"stopj(1.0)\n")
          current_cmd = None
          await notify_clients("limit_reached")  # 🔔 Notificar
        else:
          cmd = "speedj([0,-0.5,0,0,0,0], 1.0, 0.1)\n"
          r_socket.send(cmd.encode("utf-8"))
        
      elif current_cmd == "hombro_derecha":
        limit = JOINT_LIMITS[1][1]  # límite superior J1
        if joints[1] >= limit - SAFE_MARGIN:
          print("[SAFETY] Límite cercano en J1 (derecha). Parando.")
          r_socket.send(b"stopj(1.0)\n")
          current_cmd = None
          await notify_clients("limit_reached")  # 🔔 Notificar
        else:
          cmd = "speedj([0,0.5,0,0,0,0], 1.0, 0.1)\n"
          r_socket.send(cmd.encode("utf-8"))
          
      elif current_cmd == "codo_izquierda":
        limit = JOINT_LIMITS[2][0]  # límite inferior (-80°)
        if joints[2] <= limit + SAFE_MARGIN:
            print("[SAFETY] Límite cercano en J2 (izquierda). Parando.")
            r_socket.send(b"stopj(1.0)\n")
            current_cmd = None
            await notify_clients("limit_reached")
        else:
            cmd = "speedj([0,0,-0.5,0,0,0], 1.0, 0.1)\n"
            r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "codo_derecha":
        limit = JOINT_LIMITS[2][1]  # límite superior (+80°)
        if joints[2] >= limit - SAFE_MARGIN:
            print("[SAFETY] Límite cercano en J2 (derecha). Parando.")
            r_socket.send(b"stopj(1.0)\n")
            current_cmd = None
            await notify_clients("limit_reached")
        else:
            cmd = "speedj([0,0,0.5,0,0,0], 1.0, 0.1)\n"
            r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "muneca1_izquierda":
          limit = JOINT_LIMITS[3][0]  # límite inferior (-300°)
          if joints[3] <= limit + SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J4 (muñeca 1 izquierda). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,-0.5,0,0], 1.0, 0.1)\n"  # mueve solo J4 en - sentido
              r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "muneca1_derecha":
          limit = JOINT_LIMITS[3][1]  # límite superior (+300°)
          if joints[3] >= limit - SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J4 (muñeca 1 derecha). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,0.5,0,0], 1.0, 0.1)\n"  # mueve solo J4 en + sentido
              r_socket.send(cmd.encode("utf-8"))
        
      elif current_cmd == "muneca2_izquierda":
          limit = JOINT_LIMITS[4][0]  # límite inferior (-300°)
          if joints[4] <= limit + SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J5 (muñeca 2 izquierda). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,0,-0.5,0], 1.0, 0.1)\n"  # mueve solo J5 en - sentido
              r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "muneca2_derecha":
          limit = JOINT_LIMITS[4][1]  # límite superior (+300°)
          if joints[4] >= limit - SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J5 (muñeca 2 derecha). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,0,0.5,0], 1.0, 0.1)\n"  # mueve solo J5 en + sentido
              r_socket.send(cmd.encode("utf-8"))
              
      elif current_cmd == "muneca3_izquierda":
          limit = JOINT_LIMITS[5][0]  # límite inferior (-300°)
          if joints[5] <= limit + SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J6 (muñeca 3 izquierda). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,0,0,-0.5], 1.0, 0.1)\n"  # mueve solo J6 en - sentido
              r_socket.send(cmd.encode("utf-8"))

      elif current_cmd == "muneca3_derecha":
          limit = JOINT_LIMITS[5][1]  # límite superior (+300°)
          if joints[5] >= limit - SAFE_MARGIN:
              print("[SAFETY] Límite cercano en J6 (muñeca 3 derecha). Parando.")
              r_socket.send(b"stopj(1.0)\n")
              current_cmd = None
              await notify_clients("limit_reached")
          else:
              cmd = "speedj([0,0,0,0,0,0.5], 1.0, 0.1)\n"  # mueve solo J5 en + sentido
              r_socket.send(cmd.encode("utf-8"))


      elif current_cmd in CARTESIAN_VELOCITY:

          # Leer estado del TCP
          tcp_pose = rtde_r.getActualTCPPose()
          tcp_speed = rtde_r.getActualTCPSpeed()

          velocity = CARTESIAN_VELOCITY[current_cmd]

          # Determinar eje de movimiento

          if current_cmd in ("arriba", "abajo"):
              axis = 2
              axis_name = "Z"
              lower_limit = Z_MIN
              upper_limit = Z_MAX
              margin = Z_MARGIN

          elif current_cmd in ("adelante", "atras"):
              axis = 0
              axis_name = "X"
              lower_limit = X_MIN
              upper_limit = X_MAX
              margin = X_MARGIN

          elif current_cmd in ("izquierda", "derecha"):
              axis = 1
              axis_name = "Y"
              lower_limit = Y_MIN
              upper_limit = Y_MAX
              margin = Y_MARGIN

          position = tcp_pose[axis]
          actual_speed = tcp_speed[axis]
          command_speed = velocity[axis]

          # Estimar frenado solo en el sentido
          # en el que se está solicitando avanzar
          speed_toward_limit = max(
              0.0,
              actual_speed * (
                  1 if command_speed > 0 else -1
              )
          )

          braking_distance = (
              speed_toward_limit ** 2
          ) / (2 * STOPL_ACCEL)

          reserve = margin + braking_distance

          # Comprobar el límite en la dirección
          # de movimiento solicitada
          limit_reached = (
              (
                  command_speed > 0
                  and position >= upper_limit - reserve
              )
              or
              (
                  command_speed < 0
                  and position <= lower_limit + reserve
              )
          )

          if limit_reached:
              current_cmd = None

              print(
                  f"[LIMIT] Eje {axis_name}: "
                  f"{position:.4f} m"
              )

              r_socket.sendall(
                  f"stopl({STOPL_ACCEL})\n".encode("utf-8")
              )

              await notify_clients("limit_reached")

          else:
              cmd = (
                  f"speedl({velocity}, "
                  f"{CARTESIAN_ACCEL}, "
                  f"{CARTESIAN_TIME})\n"
              )

              r_socket.sendall(cmd.encode("utf-8"))


      # si current_cmd is None, no enviamos speedj
    except Exception as e:
      print("[UR] Error enviando comando:", e)
    await asyncio.sleep(0.008)  # ~125 Hz


# Cada vez que un cliente HTML se conecta, llama a handle_client.
# Mientras tanto, arranca el bucle motion_loop que sigue mandando comandos a UR según el estado.
async def main():
  # ip address wifi meta quest 2: 192.168.0.116 ajustar el host con otro last number
  # ip address wifi pc: ipconfig en cmd> 
  # Adaptador de LAN inalámbrica Wi-Fi:
  #    Dirección IPv4. . . . . . . . . . . . . . : 192.168.0.115
  #    Máscara de subred . . . . . . . . . . . . : 255.255.255.0
  #    Puerta de enlace predeterminada . . . . . : 192.168.0.1
    host = "0.0.0.0" #Escuchando en todas las interfaces: ws://0.0.0.0:8765 queda abierta a todas las interfaces
    # en unity en websocket url usar la misma del pc> ws://192.168.0.115:8765
    port = 8765

    print("=====================================")
    print("✅ Servidor WebSocket corriendo para Meta Quest")
    print(f"   Escuchando en todas las interfaces: ws://{host}:{port}")
    print("   Conéctate desde Quest usando la IP real de este PC en la red WiFi")
    print("=====================================")

    async with websockets.serve(handle_client, host, port):
        await motion_loop()  # mantiene el bucle vivo

# Arranca el programa asíncrono.
# Lanza tanto el servidor WebSocket como el bucle de control del robot.
if __name__ == "__main__":
  asyncio.run(main())

# - current_cmd → une ambos mundos: el navegador decide el estado, el bucle de movimiento lo traduce en comandos URScript reales.
# - motion_loop → ejecuta en tiempo real los comandos hacia el robot a 125 Hz.
# - handle_client → escucha lo que mande la web y actualiza el estado.

# aunque no presiones ningún botón, el motion_loop sigue corriendo en segundo plano, pero sin enviar comandos (porque current_command == "stop").

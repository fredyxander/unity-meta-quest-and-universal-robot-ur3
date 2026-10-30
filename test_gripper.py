
import socket

ROBOT_IP = "157.253.197.179"
ROBOT_PORT = 30002

def enviar(comando):
    with socket.create_connection(
        (ROBOT_IP, ROBOT_PORT),
        timeout=5
    ) as sock:
        sock.sendall((comando + "\n").encode("utf-8"))
        print(f"[UR] Enviado: {comando}")

print("1. Abrir gripper")
print("2. Cerrar gripper")
print("0. Salir")

opcion = input("Selecciona: ").strip()

try:
    if opcion == "1":
        enviar("set_tool_digital_out(0, True)")

    elif opcion == "2":
        confirmacion = input(
            "¿Zona de agarre despejada? (si/no): "
        ).strip().lower()

        if confirmacion == "si":
            enviar("set_tool_digital_out(0, False)")

except OSError as e:
    print("[ERROR]", e)

import rtde_receive
# import math

ROBOT_IP = "157.253.197.179"

# rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

# joints = rtde_r.getActualQ()

# print("HOME en grados:")
# print([round(math.degrees(q), 2) for q in joints])

# print("\nHOME en radianes:")
# print([round(q, 5) for q in joints])

# print("\nComando HOME:")
# print(
#     f"HOME_JOINTS = {repr(joints)}"
# )

# import rtde_receive

# ROBOT_IP = "IP_DE_URSIM"

rtde_r = rtde_receive.RTDEReceiveInterface(ROBOT_IP)

tcp = rtde_r.getActualTCPPose()

print("TCP:", tcp)
print("Z_HOME:", tcp[2], "metros")
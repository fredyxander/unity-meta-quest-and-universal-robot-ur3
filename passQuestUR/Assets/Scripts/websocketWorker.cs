using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;   // Necesario para TextMeshPro
using WebSocketSharp;
public class websocketWorker : MonoBehaviour
{
    public string url;
    WebSocket ws;
    public bool IsConnected => ws != null && ws.IsAlive;
    [SerializeField] private TMP_Text conectionStatus;   // Arrastra tu objeto TextMeshPro en el inspector del objeto asociado a este script "WEbSocketManager"
    [SerializeField] private GameObject displayControlPanel; //GameObject de comandos
    public robotCommands uiRobotManager;  // referencia al script websocketWorker

    // Start is called before the first frame update
    void Start()
    {
        // Estado inicial por defecto
        UpdateConnectionStatus("Esperando conexi�n...", Color.gray);

        // Asegurarse de que el boton arranque oculto
        if (displayControlPanel != null)
            displayControlPanel.SetActive(false);// SetActive oculta/muestra gameObject
    }


    // M�todo que puedes llamar desde un bot�n
    public void ConnectToServer()
    {
        if (ws != null && ws.IsAlive)
        {
            Debug.Log("Ya est�s conectado al servidor WebSocket");
            return;
        }

        ws = new WebSocket(url);

        ws.OnOpen += (sender, e) =>
        {
            Debug.Log("Conectado al servidor WebSocket");
            UpdateConnectionStatus("Conectado", Color.green);

            if (displayControlPanel != null)
                displayControlPanel.SetActive(IsConnected);
        };

        ws.OnMessage += (sender, e) =>
        {
            Debug.Log("Mensaje recibido: " + e.Data);
            if (e.Data == "limit_reached")
            {
                uiRobotManager.UpdateJointStatus("L�mite alcanzado", Color.red);
            }
        };

        ws.OnClose += (sender, e) =>
        {
            Debug.LogWarning("Conexi�n cerrada");
            UpdateConnectionStatus("Desconectado", Color.red);

            if (displayControlPanel != null)
                displayControlPanel.SetActive(false);
        };

        ws.OnError += (sender, e) =>
        {
            Debug.LogError("Error: " + e.Message);
            UpdateConnectionStatus("Error de conexi�n", Color.yellow);
        };

        ws.Connect();
    }

    //Metodo para enviar comando a robot
    public void SendCommand(string cmd)
    {
        if (ws != null && ws.IsAlive)
        {
            ws.Send(cmd);
            Debug.Log("Enviado: " + cmd);
            if(cmd != null)
            {
                uiRobotManager.UpdateJointStatus("En movimiento...", Color.green);
            }
        }
        else
        {
            Debug.LogWarning("No conectado al servidor WebSocket");
            UpdateConnectionStatus("No conectado", Color.gray);
        }
    }

    // Cerrar conexi�n con un bot�n
    public void DisconnectFromServer()
    {
        if (ws != null)
        {
            ws.Close();
            Debug.Log("Conexi�n cerrada manualmente");
            UpdateConnectionStatus("Desconectado", Color.red);

            if (displayControlPanel != null)
                displayControlPanel.SetActive(false);
        }
    }

    // Actualiza el texto de conexi�n del robot en pantalla
    private void UpdateConnectionStatus(string message, Color color)
    {
        if (conectionStatus != null)
        {
            conectionStatus.text = "Conexi�n Robot: " + message;
            conectionStatus.color = color;
        }
    }
}

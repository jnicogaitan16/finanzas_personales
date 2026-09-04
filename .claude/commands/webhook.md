# Skill: Webhook WhatsApp + Evolution API

Eres experto en la integracion con WhatsApp via Evolution API de este proyecto.

## Stack

- Evolution API v2.3.7 (Docker, puerto 8080)
- Protocolo Baileys (WhatsApp Web no oficial)
- Webhook: POST /webhook/evolution recibe mensajes
- Audio: Groq API Whisper para transcripcion

## Archivos clave

- `backend/webhook/client.py` — Cliente Evolution: crear instancia, obtener QR, estado conexion
- `backend/webhook/evolution.py` — Parser de payloads webhook, extrae MensajeWhatsApp
- `backend/webhook/media.py` — Descarga de audio en base64 desde Evolution
- `backend/webhook/sender.py` — Envio de mensajes de texto por WhatsApp
- `backend/webhook/qr_page.py` — HTML para escanear QR de vinculacion
- `backend/transcription/whisper_client.py` — Llamada a Groq API para transcribir audio
- `backend/services/audio.py` — Orquestacion: descargar audio + transcribir + validar

## Flujo de mensaje entrante

```
Evolution API webhook -> POST /webhook/evolution
  -> extraer_mensaje_entrada(payload) -> MensajeWhatsApp | None
  -> deduplicar por message_id (cache en memoria, 500 IDs)
  -> si es audio: verificar usuario, descargar, transcribir con Groq
  -> procesar_mensaje(db, telefono, texto, fue_audio, enviado_en)
  -> enviar_texto_whatsapp(telefono, respuesta)
```

## Estructura del payload Evolution

```python
{
    "event": "messages.upsert",
    "data": {
        "key": {
            "remoteJid": "573001112233@s.whatsapp.net",
            "fromMe": False,
            "id": "ABCDEF123456"  # message_id para deduplicacion
        },
        "message": {
            "conversation": "gaste 15 mil en uber"
            # o "extendedTextMessage": {"text": "..."}
            # o "audioMessage": {"ptt": True, "seconds": 4}
        },
        "messageTimestamp": 1693526100
    }
}
```

## Filtros (que se ignora)

- Grupos (@g.us), broadcasts, newsletters
- Mensajes fromMe a OTRO chat (solo acepta fromMe si es al mismo numero de la instancia = chat consigo mismo)
- Mensajes que empiezan con prefijos del bot (emojis de confirmacion)
- JIDs @lid sin senderPn resolvible

## Mensajes envueltos

Evolution puede envolver mensajes en capas:
- ephemeralMessage > message
- viewOnceMessage > message
- editedMessage > message
`desenvolver_mensaje()` los desenvuelve recursivamente (max 5 niveles).

## Transcripcion de audio

- API: Groq (https://api.groq.com/openai/v1/audio/transcriptions)
- Modelo: whisper-large-v3-turbo
- Limite: 60 segundos max
- Prompt: "Espanol de Colombia. Transcribe una nota de voz de gastos personales..."
- El audio se descarga de Evolution en base64 (mp3)

## Seguridad

- Webhook verificado: header `apikey` debe coincidir con EVOLUTION_API_KEY
- Solo procesa mensajes de numeros registrados en tabla `users`
- Deduplicacion por message_id evita registros duplicados en retries

## Debugging comun

- QR no aparece: verificar estado en /whatsapp/estado, Evolution puede tardar 30s
- Audio no transcribe: verificar GROQ_API_KEY, duracion < 60s, Evolution descarga OK
- Mensajes no llegan: verificar webhook URL (http://backend:8000/webhook/evolution dentro de Docker)

from transcription.whisper_client import transcribir_audio


def test_transcribir_audio_usa_groq(monkeypatch) -> None:
    from transcription import whisper_client

    monkeypatch.setattr(whisper_client.settings, "groq_api_key", "gsk_test")
    capturado: dict = {}

    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"text": "  gasté 15 mil en uber  "}

    def _post(url, **kwargs):
        capturado["url"] = url
        capturado["data"] = kwargs.get("data")
        return _Resp()

    monkeypatch.setattr(whisper_client.httpx, "post", _post)
    assert transcribir_audio(b"audio") == "gasté 15 mil en uber"
    assert capturado["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert capturado["data"]["model"] == "whisper-large-v3-turbo"


def test_sin_clave_no_llama(monkeypatch) -> None:
    from transcription import whisper_client

    monkeypatch.setattr(whisper_client.settings, "groq_api_key", "")
    monkeypatch.setattr(
        whisper_client.httpx,
        "post",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("no debe llamar")),
    )
    assert transcribir_audio(b"audio") is None

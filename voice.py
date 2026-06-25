import os
import tempfile
import threading
import logging

log = logging.getLogger(__name__)

_model      = None
_model_lock = threading.Lock()


def _get_whisper():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                try:
                    from faster_whisper import WhisperModel
                    _model = WhisperModel("small", device="cuda", compute_type="float16")
                    log.info("Whisper carregado (GPU)")
                except Exception:
                    try:
                        from faster_whisper import WhisperModel
                        _model = WhisperModel("small", device="cpu", compute_type="int8")
                        log.info("Whisper carregado (CPU)")
                    except Exception as e:
                        log.warning("Whisper não disponível: %s", e)
                        _model = None
    return _model


def transcribe(audio_bytes: bytes, language: str = "pt") -> str:
    model = _get_whisper()
    if model is None:
        return ""
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    try:
        segments, _ = model.transcribe(tmp, language=language)
        return " ".join(s.text for s in segments).strip()
    except Exception as e:
        log.error("Erro transcrição: %s", e)
        return ""
    finally:
        os.unlink(tmp)


def speak(text: str) -> bytes:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        engine.save_to_file(text, tmp)
        engine.runAndWait()
        with open(tmp, "rb") as f:
            audio = f.read()
        os.unlink(tmp)
        return audio
    except Exception as e:
        log.warning("TTS não disponível: %s", e)
        return b""

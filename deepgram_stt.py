from deepgram import DeepgramClient

import config

_client = DeepgramClient(api_key=config.DEEPGRAM_API_KEY)


def transcribe(audio_bytes: bytes, mimetype: str = "audio/ogg") -> str:
    """Transcribe raw audio bytes (Hindi/English/mixed) to plain text via Deepgram."""
    response = _client.listen.v1.media.transcribe_file(
        request=audio_bytes,
        model=config.DEEPGRAM_MODEL,
        smart_format=True,
        punctuate=True,
        detect_language=True,
    )
    return response.results.channels[0].alternatives[0].transcript

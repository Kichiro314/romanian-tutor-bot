import os
import subprocess
import tempfile
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

VOICE_RO = "ro-RO-AlinaNeural"


async def synthesize(text: str) -> BytesIO | None:
    """Convert Romanian text to OGG OPUS voice bytes using edge-tts + ffmpeg."""
    try:
        import edge_tts

        communicate = edge_tts.Communicate(text, VOICE_RO)
        mp3_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_data += chunk["data"]

        if not mp3_data:
            logger.warning("TTS: edge-tts returned empty audio")
            return None

        mp3_fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
        ogg_path = mp3_path[:-4] + ".ogg"
        try:
            with os.fdopen(mp3_fd, "wb") as f:
                f.write(mp3_data)

            subprocess.run(
                ["ffmpeg", "-i", mp3_path, "-c:a", "libopus", "-b:a", "32k", "-y", ogg_path],
                check=True,
                capture_output=True,
                timeout=30,
            )

            with open(ogg_path, "rb") as f:
                buf = BytesIO(f.read())
            buf.seek(0)
            return buf
        finally:
            if os.path.exists(mp3_path):
                os.unlink(mp3_path)
            if os.path.exists(ogg_path):
                os.unlink(ogg_path)

    except FileNotFoundError:
        logger.warning("TTS: ffmpeg not found — voice output disabled")
        return None
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None

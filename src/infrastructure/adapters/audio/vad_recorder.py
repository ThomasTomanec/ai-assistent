import asyncio
import numpy as np
import webrtcvad
import structlog

logger = structlog.get_logger()


class VADRecorder:
    def __init__(self, audio_input, stream=None, vad_aggressiveness=2, sample_rate=16000):
        self.audio_input = audio_input
        self.stream = stream
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        self.sample_rate = sample_rate
        self.frame_duration_ms = 30
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)  # 480 samples for 30 ms

    async def record_until_silence(self, max_duration=6, silence_duration=0.5, min_speech_frames=10):
        """
        Nahrává audio, dokud nedetekuje ticho.

        Args:
            max_duration: Maximální délka nahrávky v sekundách
            silence_duration: Délka ticha pro ukončení v sekundách
            min_speech_frames: Minimální počet speech framů před detekcí ticha (prevence předčasného ukončení)
        """
        buffer = np.array([], dtype=np.int16)
        silence_frames = 0
        speech_frames = 0  # NOVÉ: počítadlo speech framů
        speech_started = False  # NOVÉ: flag že už mluvíš

        # Zkráceno z 0.4s na 0.5s (kompromis)
        max_silence_frames = int(silence_duration * 1000 / self.frame_duration_ms)

        start_time = asyncio.get_event_loop().time()
        chunk_cache = np.array([], dtype=np.int16)

        logger.info("vad_recording_started",
                    max_duration=max_duration,
                    silence_duration=silence_duration,
                    min_speech_frames=min_speech_frames)

        while True:
            frame = await self.audio_input.read_chunk(self.stream)
            if frame is None or len(frame) == 0:
                logger.warning("empty_frame_received")
                break

            # Přidat do cache kvůli vyrovnání do frame_size
            chunk_cache = np.concatenate((chunk_cache, frame))

            while len(chunk_cache) >= self.frame_size:
                current_frame = chunk_cache[:self.frame_size]
                chunk_cache = chunk_cache[self.frame_size:]

                # VAD vyžaduje bytový buffer stejné délky (frame_size * 2 bytes per sample)
                try:
                    is_speech = self.vad.is_speech(current_frame.tobytes(), self.sample_rate)
                except Exception as e:
                    logger.error("vad_frame_error", error=str(e))
                    is_speech = False

                if is_speech:
                    silence_frames = 0
                    speech_frames += 1

                    # NOVÉ: Označit že začal mluvit
                    if speech_frames >= min_speech_frames and not speech_started:
                        speech_started = True
                        logger.info("speech_detected", speech_frames=speech_frames)
                else:
                    # NOVÉ: Počítej ticho pouze pokud už mluvil!
                    if speech_started:
                        silence_frames += 1
                    # Jinak ignoruj ticho před začátkem řeči

                buffer = np.concatenate((buffer, current_frame))

                # OPTIMALIZACE: Ukončit při kratším tichu (pouze po začátku řeči)
                if speech_started and silence_frames > max_silence_frames:
                    logger.info("vad_silence_detected",
                                silence_frames=silence_frames,
                                silence_duration=f"{silence_duration}s",
                                total_speech_frames=speech_frames)
                    return buffer

                # OPTIMALIZACE: Zkrácena max délka nahrávky
                if asyncio.get_event_loop().time() - start_time > max_duration:
                    logger.info("vad_max_duration_reached",
                                duration=max_duration,
                                speech_frames=speech_frames)
                    return buffer

        return buffer

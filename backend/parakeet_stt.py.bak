import ctypes
import os
import numpy as np


class ParakeetSTT:
    def __init__(self):
        print("Loading Parakeet TDT 0.6B runtime...")

        self.lib_path = os.path.expanduser(
            "~/NeMo-Speech.cpp/build/bin/libnemo_speech_asr_c.so"
        )

        self.model_path = os.path.expanduser(
            "~/voice-agent/models/parakeet/parakeet-tdt-0.6b-v3.q8_0.gguf"
        )

        if not os.path.exists(self.lib_path):
            raise FileNotFoundError(
                f"NeMo ASR library not found: {self.lib_path}"
            )

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Parakeet model not found: {self.model_path}"
            )

        # Load shared library
        self.lib = ctypes.CDLL(self.lib_path)

        self._setup_api()

        # Keep these alive for the lifetime of the recognizer.
        self.backend = BackendConfig()
        self.backend.size = ctypes.sizeof(BackendConfig)
        self.backend.gpu = 0

        self.model = ModelConfig()
        self.model.size = ctypes.sizeof(ModelConfig)
        self.model.path = self.model_path.encode()
        self.model.name = None

        self.config = RecognizerConfig()
        self.config.size = ctypes.sizeof(RecognizerConfig)
        self.config.backend = ctypes.pointer(self.backend)
        self.config.model = ctypes.pointer(self.model)
        self.config.streaming = None
        self.config.decoder = None
        self.config.vad = None
        self.config.endpointing = None
        self.config.postproc = None
        self.config.diar = None
        self.config.batching = None

        self.recognizer = ctypes.c_void_p()

        status = self.lib.nemo_speech_asr_create(
            ctypes.byref(self.config),
            ctypes.byref(self.recognizer),
        )

        if status != 0:
            error = self.lib.nemo_speech_asr_last_error()
            if error:
                error = error.decode(errors="replace")
            else:
                error = "unknown error"

            raise RuntimeError(
                f"nemo_speech_asr_create failed: {error}"
            )

        print("Parakeet loaded.")
        print(f"Model: {self.model_path}")
        print("Backend: Vulkan GPU 0")
        print("Runtime: persistent")

    def _setup_api(self):
        """
        Configure ctypes signatures for the NeMo ASR C ABI.
        """

        # void nemo_speech_asr_destroy(...)
        self.lib.nemo_speech_asr_destroy.argtypes = [
            ctypes.c_void_p
        ]
        self.lib.nemo_speech_asr_destroy.restype = None

        # const char* nemo_speech_asr_last_error(void)
        self.lib.nemo_speech_asr_last_error.argtypes = []
        self.lib.nemo_speech_asr_last_error.restype = ctypes.c_char_p

        # create()
        self.lib.nemo_speech_asr_create.argtypes = [
            ctypes.POINTER(RecognizerConfig),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.lib.nemo_speech_asr_create.restype = ctypes.c_int

        # recognition options default
        self.lib.nemo_speech_asr_recognition_options_default.argtypes = []
        self.lib.nemo_speech_asr_recognition_options_default.restype = (
            RecognitionOptions
        )

        # recognize_f32()
        self.lib.nemo_speech_asr_recognize_f32.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(RecognitionOptions),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_size_t,
            ctypes.c_int32,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self.lib.nemo_speech_asr_recognize_f32.restype = ctypes.c_int

        # result transcript
        self.lib.nemo_speech_asr_result_transcript.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]
        self.lib.nemo_speech_asr_result_transcript.restype = ctypes.c_char_p

        # result destroy
        self.lib.nemo_speech_asr_result_destroy.argtypes = [
            ctypes.c_void_p
        ]
        self.lib.nemo_speech_asr_result_destroy.restype = None

    def transcribe(self, audio):
        """
        Transcribe one complete utterance.

        audio:
            numpy float32 mono PCM, expected at 16 kHz.
        """

        audio = np.asarray(audio, dtype=np.float32)

        if audio.size == 0:
            return ""

        # Make sure memory is contiguous for the C API.
        audio = np.ascontiguousarray(audio)

        # Keep audio alive while C is using it.
        samples = audio.ctypes.data_as(
            ctypes.POINTER(ctypes.c_float)
        )

        options = self.lib.nemo_speech_asr_recognition_options_default()

        # We only need the final transcript.
        options.interim_results = False

        # Parakeet is being used for English here.
        options.language_code = b"en"

        result = ctypes.c_void_p()

        status = self.lib.nemo_speech_asr_recognize_f32(
            self.recognizer,
            ctypes.byref(options),
            samples,
            audio.size,
            16000,
            ctypes.byref(result),
        )

        if status != 0 or not result:
            error = self.lib.nemo_speech_asr_last_error()

            if error:
                error = error.decode(errors="replace")
            else:
                error = "unknown error"

            print(f"Parakeet recognition failed: {error}")
            return ""

        try:
            transcript = self.lib.nemo_speech_asr_result_transcript(
                result,
                0,
            )

            if not transcript:
                return ""

            return transcript.decode(errors="replace").strip()

        finally:
            self.lib.nemo_speech_asr_result_destroy(result)

    def close(self):
        if getattr(self, "recognizer", None):
            self.lib.nemo_speech_asr_destroy(self.recognizer)
            self.recognizer = None


# ------------------------------------------------------------------
# C ABI structures
# ------------------------------------------------------------------

class BackendConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("gpu", ctypes.c_int32),
    ]


class ModelConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("path", ctypes.c_char_p),
        ("name", ctypes.c_char_p),
    ]


class RecognizerConfig(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("backend", ctypes.POINTER(BackendConfig)),
        ("model", ctypes.POINTER(ModelConfig)),
        ("streaming", ctypes.c_void_p),
        ("decoder", ctypes.c_void_p),
        ("vad", ctypes.c_void_p),
        ("endpointing", ctypes.c_void_p),
        ("postproc", ctypes.c_void_p),
        ("diar", ctypes.c_void_p),
        ("batching", ctypes.c_void_p),
    ]


class RecognitionOptions(ctypes.Structure):
    _fields_ = [
        ("size", ctypes.c_size_t),
        ("request_id", ctypes.c_char_p),
        ("language_code", ctypes.c_char_p),
        ("interim_results", ctypes.c_bool),
        ("enable_word_time_offsets", ctypes.c_bool),
        ("enable_automatic_punctuation", ctypes.c_bool),
        ("verbatim_transcripts", ctypes.c_bool),
        ("profanity_filter", ctypes.c_bool),
        ("stop_history_eou_ms", ctypes.c_int32),
        ("speech_contexts", ctypes.c_void_p),
        ("speech_context_count", ctypes.c_size_t),
        ("max_alternatives", ctypes.c_int32),
        ("enable_speaker_diarization", ctypes.c_bool),
        ("max_speaker_count", ctypes.c_int32),
    ]
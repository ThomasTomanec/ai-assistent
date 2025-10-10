"""Tests for audio module"""
import pytest
from src.audio.capture import AudioCapture

def test_audio_capture_init():
    capture = AudioCapture(sample_rate=16000, channels=1)
    assert capture.sample_rate == 16000
    assert capture.channels == 1

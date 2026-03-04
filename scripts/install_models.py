#!/usr/bin/env python3
"""Download TTS model files for OTTO voice support."""

import argparse
import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path.home() / ".otto" / "models"

KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


def download_file(url: str, dest: Path):
    """Download a file with progress indication."""
    print(f"  Downloading {dest.name}...")
    try:
        urllib.request.urlretrieve(url, dest)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  Done ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"  Error: {e}")
        raise


def install_kokoro_models():
    """Download kokoro-onnx model files to ~/.otto/models/."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in KOKORO_FILES.items():
        dest = MODELS_DIR / filename
        if dest.exists():
            print(f"  {filename} already exists, skipping")
            continue
        download_file(url, dest)


def test_connection():
    """Test connection to Rocrail."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from otto.config import load_config
    from otto.rocrail.client import RocrailClient

    config = load_config()
    rc = config["rocrail"]
    print(f"\nTesting Rocrail connection at {rc['host']}:{rc['port']}...")

    client = RocrailClient(host=rc["host"], port=rc["port"])
    result = client.connect()
    if result["success"]:
        locos = client.model.get_locomotives()
        blocks = client.model.get_blocks()
        print(f"  Connected! {len(locos)} locomotives, {len(blocks)} blocks")
        client.disconnect()
    else:
        print(f"  Connection failed: {result['error']}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Install OTTO model files")
    parser.add_argument("--test-connection", action="store_true", help="Test Rocrail connection")
    args = parser.parse_args()

    print("Installing OTTO models...")
    print(f"Models directory: {MODELS_DIR}")

    print("\nKokoro TTS models:")
    install_kokoro_models()

    print("\nfaster-whisper models will auto-download on first use.")

    if args.test_connection:
        test_connection()

    print("\nDone!")


if __name__ == "__main__":
    main()

# Smart CCTV

A Python-based smart surveillance prototype that combines real-time motion detection, live MJPEG streaming, synchronized audio-video recording, e-mail alerts, and LSB steganography for tamper-evident visual evidence.

> 🥈 **Second Prize — Student Scientific Communications Session 2026**  
> Section 03-02, **„Tehnologii Multimedia Evoluate în Aplicații Informatice”**,  
> Faculty of Automatic Control and Computers, POLITEHNICA Bucharest.

## Overview

Smart CCTV is a lightweight surveillance system designed to run locally, without requiring a dedicated GPU or a cloud processing service. The application analyzes consecutive camera frames, detects significant motion, records the event, sends an e-mail alert, and stores a protected PNG evidence image containing a hidden security code.

The project focuses on three main areas:

- real-time multimedia processing;
- local edge-computing surveillance;
- evidence-integrity verification through LSB steganography.

## Main Features

- Real-time webcam monitoring with OpenCV
- Motion detection through frame differencing and contour analysis
- Gaussian filtering, thresholding, and morphological dilation
- Automatic audio and video recording when motion is detected
- Synchronized A/V export to MP4
- Live MJPEG stream through a local Flask web interface
- E-mail alert containing a protected PNG evidence image
- LSB steganography for embedding an alert ID and timestamp
- Separate utility for extracting and validating the hidden code
- Multithreaded architecture for non-blocking capture, alerts, audio, and multiplexing
- Controlled shutdown that waits for media processing to finish

## How It Works

1. The application captures two consecutive video frames.
2. Their absolute difference is converted to grayscale.
3. Gaussian blur reduces camera noise.
4. Thresholding and dilation isolate relevant movement areas.
5. Contours smaller than the configured minimum area are ignored.
6. When motion is detected:
   - audio and video recording start;
   - the first evidence frame is saved as PNG;
   - a security string is embedded in the image using LSB steganography;
   - an e-mail alert is sent asynchronously.
7. Recording stops after the configured grace period without movement.
8. MoviePy combines the temporary audio and video files into a final MP4.
9. `verifica_stegano.py` can extract the hidden security code from the PNG evidence.

## Technologies

- **Python**
- **OpenCV** — video capture and image processing
- **Flask** — local web interface and MJPEG streaming
- **NumPy** — matrix and bit-level operations
- **SoundDevice** — audio capture
- **SciPy** — WAV file generation
- **MoviePy / FFmpeg** — audio-video synchronization and MP4 export
- **SMTP / MIME** — e-mail alerts
- **Threading** — concurrent processing

## Project Structure

```text
Smart-CCTV/
├── SmartCCTV.py          # Main surveillance application
├── verifica_stegano.py   # LSB evidence verification utility
├── Documentatie.docx     # Technical documentation
├── Prezentare CCTV.pptx  # Project presentation
├── folder_video/         # Generated recordings
└── folder_stegano/       # Protected PNG evidence images
```

The output folders are created automatically when the application starts.

## Requirements

- Python 3.8 or newer
- Webcam
- Microphone
- Network connection for e-mail alerts
- FFmpeg support for MoviePy

## Installation

Clone the repository:

```bash
git clone https://github.com/sovarares/Smart-CCTV.git
cd Smart-CCTV
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install opencv-python numpy sounddevice scipy Flask moviepy==1.0.3 imageio-ffmpeg
```

## E-mail Configuration

**Do not store e-mail passwords directly in the source code.**

Update `SmartCCTV.py` to read the configuration from environment variables:

```python
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
```

Set the variables before running the project.

Windows PowerShell:

```powershell
$env:EMAIL_SENDER="sender@gmail.com"
$env:EMAIL_PASSWORD="your-app-password"
$env:EMAIL_RECEIVER="receiver@example.com"
```

Linux/macOS:

```bash
export EMAIL_SENDER="sender@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_RECEIVER="receiver@example.com"
```

Use an application-specific password instead of the main account password.

## Running the Application

```bash
python SmartCCTV.py
```

Open the local interface in a browser:

```text
http://127.0.0.1:5000
```

To access it from another device connected to the same local network:

```text
http://<computer-local-IP>:5000
```

Use the **OPREȘTE CAMERA** button to stop the system safely and allow all active media-processing threads to finish.

## Generated Files

### Video recordings

Final recordings are stored in:

```text
folder_video/alertaN_COMPLET.mp4
```

Each final file contains synchronized video and audio.

### Protected evidence images

Evidence images are stored in:

```text
folder_stegano/dovada_alertaN.png
```

The image contains a hidden code similar to:

```text
SECURED_alertaN_HHMMSS
```

Because the evidence is stored as lossless PNG, editing or lossy recompression may destroy the embedded message and indicate that the file was altered.

## Verifying Evidence Integrity

Place the evidence image inside `folder_stegano`, then run:

```bash
python verifica_stegano.py
```

The utility scans all files matching:

```text
folder_stegano/dovada_*.png
```

A valid image produces the extracted security code. A modified or incompatible image may fail the decoding process.

## Current Limitations

- The system detects motion, not the identity or semantic class of an object.
- The Flask interface does not currently include authentication or HTTPS.
- LSB steganography is intentionally fragile and should be treated as a tamper-evident mechanism, not as encryption.
- The current prototype uses one camera and one microphone.
- E-mail delivery depends on the configured SMTP account and network connection.

## Future Development

- Multi-camera support
- Authenticated web dashboard
- Encrypted configuration management
- Cloud backup for protected evidence
- Local acoustic alarm
- Configurable motion-sensitivity controls
- Event history and recording management
- Deployment on Raspberry Pi or similar edge hardware

## Author

**Șova Ioan-Rareș**  
Faculty of Automatic Control and Computers  
POLITEHNICA Bucharest

Scientific coordinator: **Conf. dr. ing. Ștefan Mocanu**

## Academic Recognition

The project received **Second Prize** at the **2026 Student Scientific Communications Session**, in the section **„Tehnologii Multimedia Evoluate în Aplicații Informatice”**.

# FitFetch - FitGirl Repack Link Extractor

[![Version](https://img.shields.io/badge/version-1.4.1-blue.svg)](https://github.com/BrainlessDip/fitfetch)
[![Python](https://img.shields.io/badge/python-3.14+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

A modern, dark-themed GUI tool for extracting FuckingFast direct download links from FitGirl repack pages. Built with PyQt6 and zendriver

## Features

- **Extract Links**: Automatically extract FuckingFast direct download links
- **Modern UI**: Clean, dark GitHub-inspired interface
- **Smart Detection**: Automatically finds and lists all parts
- **Selective Extraction**: Choose specific parts to extract
- **Save to File**: Export links with timestamped filenames
- **Click to Select**: Click on filenames to toggle selection
- **Progress Tracking**: Real-time progress bar and status updates

## Quick Start

### Prerequisites

- Python 3.14 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/BrainlessDip/fitfetch.git
cd fitfetch
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

## Optional (Recommended): Using `uv`

You can also use [`uv`](https://github.com/astral-sh/uv), a fast Python package manager, instead of pip.

1. Install dependencies
```bash
uv sync
```

2. Run the application using uv

```bash
uv run main.py
````

## Installation Notice

Download FitFetch from the [latest release](https://github.com/BrainlessDip/FitFetch/releases/latest).

**Option 1:** Download the `.exe` installer and follow the setup wizard. Because FitFetch is currently an unsigned application, Windows Defender may occasionally flag the installer as a false positive. If this happens, open Windows Security → Protection history, restore the file, and choose "Allow on device" if prompted.

**Option 2 (Recommended):** Download the `.zip` version, extract it to a folder, and run `FitFetch.exe`. Do not delete or move the `_internal` folder, as it contains files required for the application to work.

If you're unsure, you can always scan the ZIP or executable with [VirusTotal](https://www.virustotal.com/) before running it.

## PowerShell Installers

FitFetch provides PowerShell scripts for automated installation.

### Portable.ps1 (No Install)

Downloads and runs the latest portable release without modifying your system.

```powershell
irm "https://fitfetch.pages.dev/installers/Portable.ps1" | iex
```

### Setup.ps1 (Installer)

```powershell
irm "https://fitfetch.pages.dev/installers/Setup.ps1" | iex
```

### Running on a Virtual Machine

If you prefer not to run FitFetch on your main device, you can use a cloud Windows VM.

- [AppOnFly](https://www.apponfly.com/) — Windows VPS in your browser. Note: FitGirl sites have a high block rate on cloud/VPS IPs, so extraction may be limited.

> **Tip:** Running FitFetch on your own physical device gives the best results, as cloud IPs are often blocked by FitGirl pages.

## Dependencies

```txt
beautifulsoup4>=4.15.0
pyqt6>=6.11.0
requests>=2.34.2
setuptools>=82.0.1
zendriver>=0.15.5
cloudscraper>=1.2.71
```

## Usage

### Fetching Links
1. Enter a FitGirl repack URL in the input field
2. Press `Fetch` 
3. All found parts will appear in the list

### Extracting Links
1. Select/deselect parts using checkboxes or click on filenames
2. Press `Extract`
3. Extracted links will appear in the output section

## Downloading with JDownloader (Recommended)

FitFetch extracts direct download links, making them perfect for use with [JDownloader](https://jdownloader.org/).

### Automatic Link Capture

1. Install and open JDownloader.
2. Enable the **LinkGrabber** feature (enabled by default).
3. In FitFetch, extract the download links.
4. Click **Copy** (or press `Ctrl+C`).
5. JDownloader will automatically detect the copied links and add them to **LinkGrabber**.
6. Review the package and click **Start Downloads**.

### Manual Import

If automatic detection is disabled:

1. Copy the extracted links from FitFetch.
2. In JDownloader, go to **LinkGrabber**.
3. Click **Add New Links** (or press `Ctrl+V`).
4. Confirm and start the downloads.

## Project Structure

```
fitfetch/
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── LICENSE             # AGPL-3.0 License
└── screenshot.png      # Application screenshot
```

## Build

To build the executable (.exe), run the following command:
```bash
pyinstaller --onedir --windowed --clean --noconfirm --name FitFetch --icon favicon.ico --optimize 2  --add-data "favicon.ico;." main.py
```

⚠️ This executable may be flagged by some antivirus software due to false positives commonly associated with pyinstaller compiled applications.


### Browser Issues
- Ensure Google Chrome is installed
- Chrome will open automatically during extraction

### Dependencies
- If you encounter import errors, ensure all dependencies are installed
- Try updating pip: `pip install --upgrade pip`

### Permission Issues
- On some systems, you may need to run with administrative privileges
- Ensure you have write permissions for saving files

## Acknowledgements

This project was inspired by the excellent work of **FitGirl FF Link Extractor** by **zouhirdev**:

- https://github.com/zouhirdev/fitgirl-ff-link-extractor

FitFetch started as a personal rewrite with a different approach while building upon the original idea. It introduces several improvements, including:

- **Dual extraction engines** (V1 for speed, V2 for improved reliability)
- **Configurable extraction delay** to help avoid rate limits
- **Modern dark UI**
- **Part selection and batch extraction**
- **Improved progress reporting and status updates**
- **Quality-of-life features** such as copy, save, and update checking

A huge thank you to [zouhirdev](https://github.com/zouhirdev) for creating the original project and sharing it with the community. Without that work, FitFetch would not exist in its current form. I will always be grateful for the inspiration and foundation it provided.

## Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the AGPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational purposes only. Please respect the content providers' terms of service and use this tool responsibly.

## Contact

- **Issues**: [GitHub Issues](https://github.com/BrainlessDip/fitfetch/issues)
- **Discussions**: [GitHub Discussions](https://github.com/BrainlessDip/fitfetch/discussions)
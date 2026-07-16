# FitFetch - FitGirl Repack Link Extractor

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/BrainlessDip/fitfetch)
[![Python](https://img.shields.io/badge/python-3.14+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

A modern, dark-themed GUI tool for extracting FuckingFast direct download links from FitGirl repack pages. Built with PyQt6 and nodriver

## Features

- **Extract Links**: Automatically extract FuckingFast direct download links
- **Modern UI**: Clean, dark GitHub-inspired interface
- **Smart Detection**: Automatically finds and lists all parts
- **Selective Extraction**: Choose specific parts to extract
- **Copy to Clipboard**: Quick copy with Ctrl+C
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

## Dependencies

```txt
beautifulsoup4>=4.15.0
cloudscraper>=1.2.71
nodriver>=0.50.3
pyqt6>=6.11.0
requests>=2.34.2
setuptools>=82.0.1
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
├── LICENSE             # MIT License
└── screenshot.png      # Application screenshot
```

## Troubleshooting

### NoDriver Issue (For now)

SyntaxError: Non-UTF-8 code starting with '\xb1' on line 1345, but no encoding declared; see https://peps.python.org/pep-0263/ for details

```bash
iconv -f ISO-8859-15 -t UTF-8 -o /app/.venv/lib/python3.14/site-packages/nodriver/cdp/network.py.new /app/.venv/lib/python3.14/site-packages/nodriver/cdp/network.py mv -f /app/.venv/lib/python3.14/site-packages/nodriver/cdp/network.py.new /app/.venv/lib/python3.14/site-packages/nodriver/cdp/network.py
```

```poweshell
$src=".venv\Lib\site-packages\nodriver\cdp\network.py"; $dst="$src.new"; Get-Content $src -Encoding Latin1 | Set-Content $dst -Encoding utf8; Move-Item -Force $dst $src
```

## Build

To build the executable (.exe), run the following command:
```bash
nuitka --standalone --windows-console-mode=disable --enable-plugin=pyqt6 --enable-plugin=upx --lto=yes --remove-output --show-progress --jobs=12 --windows-icon-from-ico=./favicon.ico --windows-disable-console --include-package=cloudscraper --include-package=requests --include-package=bs4 --include-package=nodriver --include-package=PyQt6 --include-package=urllib3 --include-data-dir="path/browsers.json" --assume-yes --include-data-file=favicon.ico=favicon.ico --onefile-no-compression main.py
```

To find the `browsers.json` directory, run the following command:
```
python -c "import cloudscraper, os; print(os.path.join(os.path.dirname(cloudscraper.__file__), 'user_agent', 'browsers.json'))"
```
⚠️ This executable may be flagged by some antivirus software due to false positives commonly associated with Nuitka-compiled applications.


### Browser Issues
- Ensure Google Chrome is installed
- Chrome will open automatically during extraction

### Dependencies
- If you encounter import errors, ensure all dependencies are installed
- Try updating pip: `pip install --upgrade pip`

### Permission Issues
- On some systems, you may need to run with administrative privileges
- Ensure you have write permissions for saving files

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
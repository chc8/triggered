name: Build Triggered Executables

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    name: Build on ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    
    strategy:
      matrix:
        include:
          - os: windows-latest
            folder_name: Triggered_Windows
            build_cmd: pyinstaller --onefile --noconsole triggered.py
          - os: macos-latest
            folder_name: Triggered_macOS
            build_cmd: pyinstaller --onefile --windowed triggered.py
          - os: ubuntu-latest
            folder_name: Triggered_Linux
            build_cmd: pyinstaller --onefile triggered.py

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11' 

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pygame pyinstaller

      - name: Build Executable with PyInstaller
        run: ${{ matrix.build_cmd }}

      - name: Prepare Release Folder (Mac/Linux)
        if: runner.os != 'Windows'
        run: |
          mkdir ${{ matrix.folder_name }}
          cp -r dist/* ${{ matrix.folder_name }}/
          cp -r assets ${{ matrix.folder_name }}/ || true
          cp README.md ${{ matrix.folder_name }}/ || true

      - name: Prepare Release Folder (Windows)
        if: runner.os == 'Windows'
        run: |
          mkdir ${{ matrix.folder_name }}
          Copy-Item -Path "dist\*" -Destination "${{ matrix.folder_name }}" -Recurse
          if (Test-Path "assets") { Copy-Item -Path "assets" -Destination "${{ matrix.folder_name }}\assets" -Recurse }
          Copy-Item -Path "README.md" -Destination "${{ matrix.folder_name }}" -ErrorAction SilentlyContinue

      - name: Upload Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.folder_name }}
          path: ${{ matrix.folder_name }}

# Official Windows Server media acquisition

`brain_v12/tools/windows_official_media_download.py` downloads media only from HTTPS subdomains of Microsoft-owned `microsoft.com` or `windows.com`, rejects redirects outside those suffixes, resumes a `.part` file only when the server honors the byte range, enforces a maximum size, and promotes the file to its final name only after SHA-256 matches an independently trusted checksum.

Example (replace the checksum with a value independently published by Microsoft for the exact media and edition):

```bash
python -m brain_v12.tools.windows_official_media_download \
  --url 'https://go.microsoft.com/fwlink/?linkid=2345730&clcid=0x409&culture=en-us&country=us' \
  --destination ./private-media/WindowsServer2025.iso \
  --trusted-sha256 '<trusted-microsoft-sha256>' \
  --max-bytes 21474836480 \
  --manifest ./private-media/windows-official-media-manifest.json
```

Do not use a guessed checksum or a hash copied from the downloaded file itself as the trusted value. If Microsoft does not publish a checksum for the selected media, use a documented trusted Microsoft verification mechanism; otherwise keep the media in a pending/unverified state and do not claim `OFFICIAL_MEDIA_VERIFIED`.

The tool never downloads during tests, never overwrites an existing destination, never modifies the source file after promotion, and never creates/partitions disks or starts a VM. A successful media download does not prove the ISO boots, Windows is installed, or the license is activated.
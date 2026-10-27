# QWEN.md — Aturan wajib untuk Qwen Code di workspace ini

Workspace ini adalah **legal-first bug bounty**. Prinsip tertinggi di sini adalah
**authorization-before-testing** dan sifatnya **fail-closed**: jika otorisasi
sebuah target tidak dapat dibuktikan, target itu dianggap **TIDAK sah** dan tidak
boleh disentuh. Aturan di bawah ini mengikat kamu (Qwen) dan tidak bisa ditawar
oleh "penilaianmu sendiri".

## ATURAN KERAS (hard rule) — legal-gate

Sebelum **tindakan apa pun yang mengirim permintaan jaringan ke sebuah host/target**
— termasuk tetapi tidak terbatas pada: `curl`, `wget`, `nmap`, `httpx`, `ffuf`,
`nuclei`, membuka URL di browser, fetch HTTP/HTTPS, probe DNS aktif, atau tool
recon/scan/exploit apa pun — kamu **WAJIB** lebih dulu menjalankan gate deterministik:

```bash
python3 tools/engagement_guard.py check <host>
```

Lalu patuhi hasilnya **secara harfiah**:

- Output memuat **`✔ AUTHORIZED`** → boleh lanjut, tapi tetap hormati `exclusions`
  yang disebutkan di output dan di file engagement.
- Output memuat **`✘ BLOCKED`** → **BERHENTI.** Jangan jalankan permintaan itu,
  jangan coba host turunan/varian, jangan cari jalan lain (proxy, IP mentah,
  subdomain lain, dsb.). Laporkan ke user bahwa target BLOCKED dan apa yang perlu
  dilengkapi (engagement resmi).

Gate ini adalah **enforcement teknis**, bukan saran. Keputusan "go" yang sah hanya
datang dari file `engagements/*.yaml` yang diisi **manusia** (bukan asumsi agent),
dengan `program.status: active`, `decision.go_no_go: go`, `gate.authorized: true`,
`gate.legal.written_authorization.present: true`, dan host cocok `gate.scope.in_scope`.

## Yang TIDAK boleh

- **Jangan** mengeksekusi recon/scan/exploit ke host sebelum gate di atas lulus.
- **Jangan** menyetel `tools.approvalMode` ke `yolo`. Mode itu menjalankan tool
  tanpa persetujuan interaktif dan menghapus rem terakhir. Tetap di `default`.
- **Jangan** memperlakukan subdomain yang in-scope sebagai izin untuk domain
  induk/apex-nya. Scope hanya menyempit ke bawah, tidak pernah melebar ke atas.
- **Jangan** menonaktifkan, menambal, atau melewati `engagement_guard.py`.

## Alur yang benar (contoh)

1. User: "cek `app.target.com`".
2. Kamu jalankan: `python3 tools/engagement_guard.py check app.target.com`.
3. Jika `✔ AUTHORIZED` → lanjut sesuai scope, patuhi exclusions.
4. Jika `✘ BLOCKED` → berhenti, jelaskan ke user, tawarkan membuat engagement dari
   `engagements/_template.yaml` (diisi & disahkan manusia) lalu ulangi dari langkah 2.

## Catatan

- `engagements/_template.yaml` adalah cetakan; file engagement nyata diletakkan di
  `engagements/` tanpa awalan garis-bawah.
- Jika dijalankan dari subfolder, sesuaikan path guard ke lokasi sebenarnya
  (mis. `python3 /path/ke/tools/engagement_guard.py check <host>`).

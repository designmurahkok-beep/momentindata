# Sistem Data Undangan Pernikahan Digital

Aplikasi web modern, mandiri (*standalone*), responsif HP/desktop, dan aman untuk pengumpulan serta manajemen data undangan pernikahan digital 2-arah (**Admin & Client Calon Pengantin**).

Dibangun secara presisi berdasarkan dokumen spesifikasi **PRD: Sistem Data Undangan Pernikahan Digital (Draf versi 1 · 21 Oktober 2026)**.

---

## 🚀 Fitur yang Telah Diimplementasikan Sesuai PRD

### 1. Portal Client (Calon Pengantin)
- **Autentikasi & Keamanan:** Login dengan username & password yang dibuatkan admin, ganti password mandiri, enkripsi kata sandi menggunakan hash PBKDF2/Werkzeug.
- **Dashboard Progres Real-Time:** Menampilkan ringkasan status 7 bagian (*Belum diisi*, *Sebagian*, *Lengkap*) dan persentase kelengkapan keseluruhan (0% s/d 100%).
- **Formulir 7 Bagian:**
  1. **Tema Undangan:** Pemilihan visual kartu tema dengan pratinjau gambar/desain, pemilihan warna aksen tema (*color palette swatch*), dan catatan permintaan khusus.
  2. **Biodata Pengantin:** Mempelai pria & wanita (Nama lengkap & gelar, nama panggilan, foto dengan pratinjau instan maks 5 MB, urutan anak, nama lengkap ayah & ibu, akun Instagram opsional).
  3. **Detail Rangkaian Acara:** Multi-acara dinamis (Akad Nikah, Resepsi, Pemberkatan, Unduh Mantu, dll) dengan nama acara, tanggal, jam mulai & selesai, nama lokasi/gedung, alamat lengkap, dan tautan Google Maps.
  4. **Love Story:** Rangkaian kisah cinta per momen/tahun dengan judul, tahun/tanggal, teks cerita, dan foto kenangan.
  5. **Kado Digital:** Multi-rekening bank, multi-dompet digital (*e-wallet*), unggah gambar QRIS / barcode rekening, serta alamat lengkap pengiriman kado fisik penerima.
  6. **Turut Mengundang:** Daftar nama keluarga besar atau tokoh dengan fitur urutan naik/turun (*reorder*).
  7. **Backsound Musik:** Pilihan lagu rekomendasi preset admin (lengkap dengan *audio player* pratinjau putar/jeda) **ATAU** unggah file lagu sendiri (maks 10 MB) beserta judul lagu & nama artis.
- **Perilaku Formulir & UX:**
  - *Autosave* otomatis dengan debounce + indikator visual (*Menyimpan...*, *Tersimpan*, *Gagal*).
  - Tanda bintang merah pada kolom wajib (`*`).
  - Tampilan sangat nyaman digunakan dari HP (*mobile-first* layout & sticky bottom navigation).
  - Tombol **"Tandai Selesai Diisi"** dengan dialog konfirmasi yang otomatis mengubah status pesanan menjadi *"Data lengkap"*.

### 2. Portal Administrator & Tim Staf
- **Dashboard Statistik:** Total Client, Menunggu Data, Data Lengkap, Sedang Dikerjakan, dan Selesai.
- **Tabel Manajemen Client:** Pencarian instan berdasarkan nama pasangan atau username, filter berdasarkan status pesanan dan kelengkapan data.
- **Kelola Akun Client:** Tambah client baru, reset password client, aktifkan / nonaktifkan akun, serta hapus data.
- **Edit Data Client (Admin Mode):** Admin dapat membuka dan mengubah formulir 7 bagian milik client mana pun secara langsung.
- **Status Pesanan Interaktif:** Dropdown status langsung pada tabel (*Menunggu data*, *Data lengkap*, *Sedang dikerjakan*, *Selesai*).
- **Catatan Internal:** Kolom catatan privat per client yang tidak terlihat oleh calon pengantin (hanya admin/staf).
- **Export Center (Unduh Data):**
  - **Paket ZIP Lengkap:** Berisi `Ringkasan_Biodata.pdf`, `Data_Undangan.xlsx`, `Data_Undangan.json`, dan seluruh file foto mempelai, love story, QRIS, serta file musik yang diunggah.
  - **Excel (.xlsx) per Client:** Spreadsheet rapi siap pakai tim desain.
  - **PDF Siap Cetak/Baca:** Dokumen PDF ringkasan biodata resmi format A4.
  - **Rekap Excel Seluruh Client:** Rekap satu file spreadsheet berisi daftar seluruh pesanan.
- **Kelola Katalog Pilihan (Master Data):**
  - Kelola Tema: Tambah tema baru, kategori, pratinjau gambar, palet warna, dan deskripsi.
  - Kelola Backsound: Tambah lagu preset baru dengan unggah file audio MP3/WAV, pemutar lagu, dan durasi.

---

## 🔑 Akun Bawaan untuk Pengujian

| Peran | Username | Password | Deskripsi |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | Akses penuh dashboard admin, tabel client, katalog tema, export data |
| **Client Demo** | `rizky_anisa` | `pass123` | Terhubung ke pesanan Rizky & Anisa dengan data contoh lengkap |

---

## 🖥️ Cara Menjalankan Aplikasi

### Cara 1: Sekali Klik di Windows
Klik ganda file:
```cmd
run.bat
```
Aplikasi akan otomatis menginisialisasi database SQLite, menghasilkan aset tema & audio sampel, menjalankan server di `http://127.0.0.1:5000`, dan membuka browser Anda.

### Cara 2: Melalui Terminal / Command Prompt
```bash
# 1. Masuk ke direktori proyek
cd C:\Users\Pongo\.gemini\antigravity\scratch\sistem-undangan-pernikahan

# 2. Jalankan aplikasi dengan Python
python app.py
```
Lalu buka browser di alamat:
👉 **http://127.0.0.1:5000**

---

## 📂 Struktur Berkas

```
sistem-undangan-pernikahan/
├── app.py                      # Server Flask, REST API, Auth, File Upload & Business Logic
├── database.py                 # Skema Database SQLite, Migrasi, & Seed Data Awal
├── export_utils.py             # Generator Excel (openpyxl), PDF (reportlab), & ZIP Bundle
├── generate_assets.py          # Script pembuat tema SVG preview dan audio sampel
├── requirements.txt            # Dependensi Python
├── run.bat                     # Windows 1-Click Launcher
├── README.md                   # Dokumentasi Lengkap
├── static/
│   ├── audio/                  # Koleksi file lagu preset MP3/WAV
│   ├── images/themes/          # File gambar pratinjau kartu tema SVG
│   └── uploads/
│       ├── music/              # Folder penyimpanan file musik unggahan client
│       ├── photos/             # Folder penyimpanan foto pengantin, QR, & love story
│       └── themes/             # Folder gambar tema baru unggahan admin
└── templates/
    ├── base.html               # Layout induk (Tailwind CSS, Lucide icons, fonts, flash alerts)
    ├── login.html              # Halaman login elegan dengan pemilih akun demo
    ├── client_dashboard.html   # Formulir 7 bagian interaktif client & mode edit admin
    └── admin_dashboard.html    # Panel admin, tabel client, katalog tema & backsound
```

---

## 💡 Jawaban & Solusi untuk "Pertanyaan Terbuka" (Bagian 9 PRD)

1. **Pembuatan Undangan Otomatis vs Manual:**
   - Sistem ini telah menyediakan ekspor **JSON**, **Excel**, dan **ZIP** lengkap. Ke depannya, data JSON ini dapat langsung disambungkan ke template renderer otomatis (Next.js / HTML Generator) tanpa mengubah struktur database yang ada saat ini.
2. **Kapasitas & Multi-Staf:**
   - Arsitektur SQLite + Flask sangat cepat dan ringan untuk puluhan hingga ratusan client per tahun. Semua staf dapat login menggunakan akun admin secara bersamaan.
3. **Penguncian Data Setelah Ditandai Selesai:**
   - Sistem mencatat penandaan `client_marked_done` beserta tanggalnya. Di tabel admin terlihat jelas siapa yang sudah selesai mengisi, dan admin dapat mengunci atau langsung memproses data tersebut.
4. **Validasi Musik & Hak Cipta:**
   - Format dan ukuran file dibatasi otomatis (< 10 MB). Admin dapat memutar dan mendengarkan langsung file audio yang diunggah sebelum menggunakannya.

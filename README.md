# DIENGIN

Dashboard monitoring AWS dan prediksi embun beku Dieng. Aplikasi hanya membaca hasil pipeline.

## Tampilan

- **Ringkasan:** prediksi tanggal target, enam parameter cuaca, grafik cuaca, dan riwayat rilis.
- **Eksplorasi data:** pilih rentang tanggal dan kolom observasi, unduh CSV, serta buka arsip malam.
- **Panduan & status:** arti probabilitas, waktu rilis, kualitas data, serta detail pembaruan.

Grafik mendukung tooltip, zoom, dan geser. Klik dua kali untuk mengembalikan rentang awal.
Rentang 6/12/24/48 jam dihitung mundur dari observasi terakhir yang tersimpan.
CSV mempertahankan satuan sumber; probabilitas pada CSV menggunakan skala 0–1.

## Menjalankan dashboard

```powershell
python -m pip install -r requirements_dashboard.txt
python -m streamlit run app.py
```

Dashboard membaca berkas pada folder `output/` dan `data/history/` relatif terhadap lokasi `app.py`.
Tanpa berkas tersebut, aplikasi menampilkan keadaan data belum tersedia.
Tidak ada data contoh yang otomatis dipakai oleh aplikasi.

## Deployment

Kode sumber berada di branch `main`. Workflow cloud menyalin `app.py`, dependensi dashboard,
hasil pipeline, dan riwayat ke branch `runtime` yang digunakan Streamlit.
Perubahan UI di `main` baru tampil setelah publikasi runtime berikutnya berhasil.
Mengedit `runtime` langsung akan ditimpa oleh pipeline.

Pemeriksaan tampilan setiap 60 detik tidak memicu pengambilan data atau model.
Umur data dihitung saat halaman dibuka, menggunakan batas operasional 30/60 menit.
Prediksi lama diberi konteks arsip; rilis hilang tidak dianggap lengkap.

## Pemeriksaan UI

Workflow `Dashboard UI checks` memeriksa sintaks, data kosong/rusak, pergantian kontrol,
timestamp WIB, serta tampilan desktop/HP dengan Playwright.
Screenshot gelap/terang tersedia dalam artifact `diengin-ui-review`.
Seluruh data pada screenshot pengujian adalah simulasi di direktori sementara.

DIENGIN merupakan prototipe penelitian, bukan peringatan resmi BMKG.

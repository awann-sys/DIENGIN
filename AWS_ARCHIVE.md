# Arsip AWS Batur Dieng sejak 2021

Sumber historis bulanan adalah ekspor Excel resmi BMKG, bukan API `/getdata`
yang membatasi rentang 24 jam. ID stasiun `STA2285`.

- Tahun lampau: `/rawdata/downloadaccesdata_year/TAHUN/aws/STA2285/MULAI/SELESAI`.
- Tahun berjalan: `/rawdata/downloadaccesdata/aws/STA2285/MULAI/SELESAI`.
- Tanggal mulai: hari pertama bulan. Tanggal akhir: hari terakhir bulan,
  atau tanggal hari ini untuk bulan berjalan. Tahun URL berubah otomatis.

Branch `aws-archive` berisi:
Branch ini menyimpan satu snapshot lengkap (seperti branch `runtime`), agar
versi database besar tidak menumpuk pada setiap pembaruan. Seluruh Excel bulanan
dan hasil data tetap ada di snapshot; riwayat commit bukan cadangan versinya.

| Lokasi | Isi |
| --- | --- |
| `raw/YYYY-MM.xlsx` | Berkas sumber tanpa perubahan |
| `observations/YYYY-MM.csv.gz` | Hasil cleaning tiap bulan sumber |
| `aws_dieng_merged.csv.gz` | Seluruh observasi digabung |
| `aws_dieng.sqlite.gz` | Database SQLite terkompresi; ekstrak sebelum digunakan |
| `archive_manifest.json` | URL sumber, jumlah baris, rentang waktu, status dan progres |

Cleaning menyamakan nama metadata, memvalidasi timestamp UTC, menambahkan waktu
WIB, membuang duplikat berdasarkan stasiun dan timestamp, serta mengosongkan
nilai dengan flag kualitas `1`. Nilai hilang tidak diisi atau diinterpolasi;
nol tetap nol. File asli dan kolom flag dipertahankan. Titik embun dihitung
dari suhu/RH yang valid. Satuan parameter tetap mengikuti definisi sumber;
tidak ada konversi hujan/angin yang diasumsikan.

Bulan sumber mengikuti tanggal UTC yang terdapat dalam ekspor. Waktu WIB
dapat masuk hari/bulan berikutnya; pemilihan tanggal di dashboard tetap WIB.
Tanggal pertama/terakhir yang tersedia dicatat, bukan disamakan dengan rentang
permintaan. Sukses download tidak menjamin semua interval sepuluh menit terisi.

Workflow `AWS historical archive` mengisi bulan sejak Januari 2021, lalu hanya
mengulang bulan error/belum selesai. Bulan sekarang dan bulan sebelumnya
diperbarui setiap run. Run dipicu sesudah pipeline operasional berhasil,
disertai cron per jam sebagai cadangan. Bulan kosong dilaporkan sebagai `empty`,
sedangkan kegagalan unduh/format sebagai `error` dan dicoba lagi.
Bulan kosong diperiksa ulang setelah tujuh hari atau jika jalur tahun sumber
berubah ketika pergantian tahun, sehingga kekosongan sementara dapat terisi.

Di Streamlit: Monitoring AWS → Eksplorasi Data AWS → Sumber histori →
Arsip tersimpan → pilih rentang WIB → Muat Data. Hasil filter dapat ditampilkan
dan diunduh tanpa meminta ulang Excel ke BMKG.


# DIENGIN

Dashboard cuaca AWS Batur Dieng dan probabilitas frost. Jalankan dengan
`pip install -r requirements_dashboard.txt` lalu `streamlit run app.py`.

Tampilan utama memakai tema terang teal, ilustrasi pegunungan dengan palet
pagi/siang/sore/senja/malam berdasarkan WIB, dan angka cuaca berukuran besar.
Ilustrasi es menandai probabilitas yang melewati ambang model, **bukan**
konfirmasi kejadian frost. Kondisi awan/hujan/kabut ilustrasi mengikuti konteks
prakiraan BMKG jika tersedia; posisi matahari/bulan bersifat ilustratif.

Perjalanan prediksi menyediakan pemilih parameter cuaca dan probabilitas model.
Grafik menampilkan nilai valid terakhir pada setiap jam yang sudah selesai,
dengan titik serta label per jam. Jam tanpa data tetap kosong. Grafik
probabilitas dibatasi pada target malam aktif. Pada HP, grafik bisa digeser
secara horizontal; kartu cuaca memakai dua kolom. Eksplorasi lanjutan dan
pengunduhan histori AWS tetap tersedia.

Monitoring juga mendukung suhu maksimum, angin maksimum, dan radiasi rata-rata/
maksimum. Data lama yang belum memiliki parameter tersebut ditampilkan sebagai
`—`; satuan yang belum terverifikasi tetap dilabeli `unit AWS`. Pembaruan ini
tidak mengubah model, jadwal pengambilan AWS, atau jadwal rilis probabilitas.

Semua grafik cuaca pada Prediksi Frost, Monitoring AWS, dan Tren & Historis
membaca arsip AWS sejak 2021, digabung dengan observasi runtime terbaru.
Arsip CSV berasal dari tabel observasi yang sama dengan database SQLite.
Nilai yang gagal QC tetap kosong; arsip menjadi acuan pada timestamp yang sama.
Grafik awal menampilkan rentang terbaru, dan filter tanggal dapat memilih tahun
sebelumnya. Kegagalan memuat arsip ditampilkan sebagai peringatan, sementara
histori runtime tetap dapat dibaca. Probabilitas model tetap berasal dari
riwayat rilis model, tanpa menghitung ulang atau mengarang prediksi historis.

Grafik cuaca menyediakan resolusi Otomatis, 10 menit (data asli), 1 jam, dan
1 hari. Pilihan resolusi asli mempertahankan semua titik, termasuk pada rentang
panjang; mode otomatis dapat merangkum harian. Agregasi memakai nilai valid
terakhir per periode, tanpa interpolasi. Untuk lebih dari 10.000 titik, grafik
memakai garis tanpa lingkaran individual agar lebih ringan; seluruh titik
tetap dipakai. Tabel dan CSV selalu berisi observasi asli. Resolusi probabilitas
tetap mengikuti rilis model, bukan dibuat menjadi prediksi per 10 menit.

Pemeriksaan tampilan dan agregasi: `python -m unittest discover -s tests`.

Kartu prediksi utama menampilkan **Skor peringatan 0–100%**. Probabilitas nol
dipetakan ke skor nol, ambang model dari konfigurasi dipetakan ke 80, dan
probabilitas satu dipetakan ke 100, menggunakan interpolasi linear pada kedua
interval. Angka skor bukan persentase peluang frost. Kartu utama menampilkan
skor dan saran preventif; grafik probabilitas, output model, dan keputusan
peringatan tetap menggunakan probabilitas serta ambang asli.

Level tampilan: Aman (hijau, skor <40), Waspada (kuning, 40 hingga <80),
dan Siaga (merah, ≥80), masing-masing dengan saran preventif. Siaga mengikuti
ambang probabilitas model; batas Waspada memakai separuh ambang tersebut
sebagai pilihan komunikasi awal, bukan ambang ilmiah yang sudah divalidasi.
Data hilang tidak diberi label Aman. Peringatan kualitas data tetap terlihat.
Panduan penutup tanaman merujuk UF/IFAS Extension, “Time to Cover Up”:
https://blogs.ifas.ufl.edu/hillsboroughco/2022/12/21/time-to-cover-up/
Tindakan perlu disesuaikan dengan tanaman, kondisi lahan, dan arahan penyuluh.

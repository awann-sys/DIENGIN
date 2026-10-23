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

Pemeriksaan tampilan dan agregasi: `python -m unittest discover -s tests`.

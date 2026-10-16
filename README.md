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

Pemeriksaan tampilan dan agregasi: `python -m unittest discover -s tests`.

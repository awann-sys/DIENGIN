# DIENGIN Cloudflare scheduler

Worker ini memicu workflow `diengin-cloud.yml` pada branch `main` setiap 15 menit,
pada menit 02, 17, 32, 47. Cloudflare menafsirkan cron dalam UTC; offset WIB
adalah tujuh jam sehingga menitnya tetap sama. Ini memicu pengambilan AWS,
monitoring, prediksi, dan publikasi runtime yang sudah ada; bukan menjalankan model di Worker.

## Pengaturan melalui dashboard Cloudflare

1. Gunakan folder `cloudflare-scheduler` pada branch `main` di GitHub.
2. Workers & Pages → Create application → Import a repository → pilih
   `awann-sys/DIENGIN`, branch `main`.
3. Atur **Root directory** ke `cloudflare-scheduler`, **Build command** kosong,
   **Deploy command** `npx wrangler deploy`. Nama Worker: `diengin-scheduler`.
4. Buat fine-grained personal access token GitHub: resource owner `awann-sys`,
   repository access **Only select repositories → DIENGIN**, repository permission
   **Actions: Read and write**. Tetapkan masa berlaku dan catat tanggal perpanjangannya.
5. Di Worker → Settings → Variables and Secrets tambahkan **Secret** bernama
   `GITHUB_TOKEN`, isi token tersebut, lalu deploy. Jangan taruh token di GitHub,
   build command, variabel plaintext, atau chat.
6. Pastikan variabel runtime sesuai `wrangler.toml`: `GITHUB_REPOSITORY`,
   `GITHUB_WORKFLOW`, `GITHUB_REF`. Pada Triggers/Cron Triggers pastikan
   `2,17,32,47 * * * *` tercantum. Perubahan cron dapat memerlukan waktu propagasi.

Jika memakai editor Worker langsung, salin `src/index.js` dan tambahkan tiga
variabel runtime serta secret di atas; buat cron yang sama secara manual.

## Validasi setelah deploy

- Tunggu satu jadwal. Workers → Observability → Logs harus mencatat `dispatched`
  atau `skipped` dengan alasan `pipeline_busy`. HTTP 401/403 biasanya perlu
  pemeriksaan masa berlaku token, izin Actions, dan akses repository.
- GitHub → DIENGIN → Actions: run baru harus bertipe **workflow_dispatch**.
  `dispatched` hanya berarti permintaan diterima; cek hasil run sampai selesai.
- Cocokkan `output/pipeline_status.json` dan `output/monitoring_latest.json`
  pada branch `runtime`. Waktu observasi AWS berbeda dari waktu pipeline berjalan.
- `/health` hanya mengecek Worker hidup, tidak menguji token atau keberhasilan cron.
- Cron GitHub yang lama tetap tersedia sebagai cadangan. Setelah Cloudflare
  terbukti stabil, cron GitHub bisa dihapus dalam perubahan terpisah. Pemeriksaan
  pipeline sibuk mengurangi duplikasi, tetapi bukan penguncian atomik; concurrency
  GitHub tetap menjadi pengaman eksekusi bersamaan.

## CLI alternatif

```sh
cd cloudflare-scheduler
npx wrangler login
npx wrangler secret put GITHUB_TOKEN
npx wrangler deploy
```

Pengujian lokal tanpa token asli: `npm test` (Node.js 22+).

Referensi: https://developers.cloudflare.com/workers/configuration/cron-triggers/
dan https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event


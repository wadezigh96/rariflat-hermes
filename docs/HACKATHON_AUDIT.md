# Audit kesiapan Hermes Plugin Hackathon — Rariflat

**Status per 9 November 2026.** Rariflat sudah melampaui plugin yang hanya berupa prompt atau skill: ia memasang tools dan hooks, belajar dari hasil panggilan lokal, menyediakan guard opt-in, serta pane Hermes Desktop. Ini sejalan dengan preferensi kontes terhadap plugin yang melakukan fungsi nyata. Juri menilai usefulness, reliability, polish, dan creativity; submission tetap memerlukan PR katalog resmi, demo X di bawah 90 detik yang menandai `@NousResearch`, serta form dengan kedua tautan. [1]

## Perbaikan audit lokal

- Penyimpanan kini memakai `plugins.plugin_storage.plugin_data_dir("rariflat")`, mengikuti `HERMES_HOME` dan profile Hermes aktif. `requires_hermes` pada manifest dan draft katalog dinaikkan ke `>=0.22.6`, batas yang menyediakan API tersebut. `RARIFLAT_DATA_DIR` tetap menjadi override eksplisit. [3] [4]
- Loop detector kini memfilter field credential dan pola secret yang dikenali sebelum membuat fingerprint, menyamakan jalur itu dengan fingerprint persistensi.
- `repeated_calls_total` kini bertambah pada setiap panggilan identik, termasuk setelah data disimpan lalu dimuat ulang.
- Handler rekomendasi dan status memakai snapshot state di bawah lock. Ini mencegah iterasi atas dictionary yang sedang berubah ketika beberapa panggilan tool terjadi bersamaan.
- README, quickstart, demo, dan draft PR kini menjelaskan bahwa rekomendasi berasal dari **nama tool yang benar-benar diamati**, bukan indeks skills terpasang. Draft katalog dirapikan sebagai YAML valid dengan deskripsi yang mudah dibaca.
- README dan quickstart dipindahkan ke SHA publik `911a10bac40ff536115f7485d4bba42186f36e83`, yaitu `main` yang ditemukan saat audit. SHA tersebut belum memuat perubahan lokal pada audit ini; setelah perubahan dipublikasikan, semua pin harus diganti menjadi SHA final yang sama.

## Status submission yang harus ditutup

PR katalog resmi [NousResearch/hermes-agent#151221](https://github.com/NousResearch/hermes-agent/pull/151221) sudah ada, tetapi halaman PR yang diperiksa menunjukkan pin `950796253faa2d9b69c3c2d1256924d18ae03e9c`. Deskripsi PR yang diperbarui pada 8 November menyebut workflow katalog berstatus `action_required` saat itu; status GitHub sekarang perlu diperiksa kembali. PR tersebut harus diperbarui agar mem-pin commit akhir dari source yang telah dipublikasikan, dan validasi katalog harus berjalan pada SHA yang persis sama. Aturan katalog mewajibkan exact 40-character SHA, metadata kemampuan yang cocok dengan kode, dan persetujuan maintainer. [2] [6]

Saya belum menguji pane pada Hermes Desktop sungguhan. Tes kontrak JavaScript hanya membuktikan normalisasi event, bukan bahwa runtime Desktop kompatibel dan menampilkan UI. Ambil screenshot nyata untuk PR serta rekam demonstrasi dari runtime aktif; jangan gunakan mock UI sebagai bukti integrasi. [5]

Pengumuman menetapkan tenggat **5:00 PM Eastern, 11 November 2026**, setara **5:00 pagi WIB, 12 November 2026**. Demo harus menunjukkan plugin bekerja, bukan hanya menjelaskan fitur. Setelah PR katalog final dan demo X tersedia, kirim kedua tautan melalui form resmi. [1]

## Validasi lokal

Working copy ini lolos **43 tes Python**, **7 tes Node**, smoke test installer, kompilasi Python, parse YAML untuk kedua manifest, pemeriksaan format SHA/compatibility, dan `git diff --check`. Hermes CLI tidak tersedia di lingkungan audit, jadi `hermes plugins validate . --install-deps` dan `hermes plugins doctor .` belum dijalankan di sini. Pemeriksaan resmi tersebut tetap wajib sebelum mengklaim source final siap katalog. Tes CLI juga tidak menggantikan uji langsung pane Desktop.

## Referensi

[1]: https://x.com/NousResearch/status/2118094256438936062 "Pengumuman resmi Hermes Agent Plugin Hackathon"
[2]: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission "Aturan submission katalog Hermes"
[3]: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins "Panduan pengembangan plugin Hermes dan penyimpanan state"
[4]: https://raw.githubusercontent.com/NousResearch/hermes-agent/v0.22.6/plugins/plugin_storage.py "API plugin_data_dir pada Hermes v0.22.6"
[5]: https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk "Panduan Hermes Desktop Plugin SDK"
[6]: https://github.com/NousResearch/hermes-agent/pull/151221 "PR katalog resmi Rariflat"

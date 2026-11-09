# Audit kesiapan Hermes Plugin Hackathon — Rariflat

**Status per 9 November 2026.** Source yang diaudit dipublikasikan pada branch `main` sebagai commit [`c5d6fba59c85eddfe75e2d890dfd0bc678060aa6`](https://github.com/wadezigh96/rariflat-hermes/commit/c5d6fba59c85eddfe75e2d890dfd0bc678060aa6). README, quickstart, dan draft katalog lokal dipin ke SHA yang sama. Demo Desktop/X belum direkam.

Rariflat memasang tools dan hooks, belajar dari hasil panggilan lokal, menyediakan guard opt-in, serta pane Hermes Desktop. Ini lebih dari plugin prompt/skill dan sesuai arah kontes yang mencari plugin berfungsi nyata. Juri menilai usefulness, reliability, polish, dan creativity. [1]

## Perbaikan audit yang dipublikasikan

- Penyimpanan memakai `plugins.plugin_storage.plugin_data_dir("rariflat")`, mengikuti `HERMES_HOME` dan profile aktif secara dinamis. Manifest dan draft katalog menetapkan `requires_hermes: ">=0.22.6"`; `RARIFLAT_DATA_DIR` tetap menjadi override eksplisit. [3] [4]
- Loop detector menyaring field credential dan pola secret yang dikenali sebelum membuat fingerprint.
- `repeated_calls_total` bertambah pada setiap panggilan identik, termasuk setelah simpan/muat ulang.
- Handler rekomendasi/status membaca snapshot di bawah lock; regression test mencakup akses konkuren dan perpindahan profile.
- Dokumentasi menjelaskan bahwa rekomendasi hanya memakai nama tool yang diamati, bukan indeks skill terpasang.

## Validasi source

Pada commit persis `c5d6fba59c85eddfe75e2d890dfd0bc678060aa6`, Hermes Agent v0.23.0 melaporkan `Validation passed` untuk `hermes plugins validate . --install-deps`; `hermes plugins doctor .` juga lulus dan menemukan 3 tools serta 2 hooks.

**43 tes Python** dan **7 tes Node** lulus; smoke test installer, kompilasi Python, parse YAML, pengecekan metadata dan pin, serta `git diff --check` juga lulus. Source dipush fast-forward ke `main`, tanpa force push. Workflow GitHub untuk commit itu terlihat berjalan saat diperiksa; periksa tautan Actions di repo untuk hasil akhir.

## PR katalog resmi dan akses

PR katalog resmi [NousResearch/hermes-agent#151221](https://github.com/NousResearch/hermes-agent/pull/151221) masih terbuka dari branch `feat/add-rariflat-plugin-catalog` di fork `wadezigh96/hermes-agent`. Entry yang dibaca di branch itu masih mem-pin `4627c41da2f8906c5927dabc19f93e3acb9e685c` dan mensyaratkan Hermes `>=0.21`; seharusnya diperbarui ke source tervalidasi di atas dan `>=0.22.6`. [2] [6]

Saya mencoba memperbarui file katalog pada branch PR tersebut, tetapi GitHub menolak operasi tulis dengan **403 `Resource not accessible by integration`**. Tidak ada perubahan yang dilakukan pada fork atau PR. Akses GitHub yang tersedia untuk sesi ini tidak mencakup izin tulis ke `wadezigh96/hermes-agent`; untuk menyelesaikan langkah ini, aktifkan izin connector untuk repo itu atau lakukan commit berikut secara manual pada branch PR:

```yaml
sha: c5d6fba59c85eddfe75e2d890dfd0bc678060aa6
requires_hermes: ">=0.22.6"
```

Setelah push ke branch PR, pantau validasi katalog dan tangani kebutuhan persetujuan maintainer; saya tidak mengubah permission atau mencoba jalur autentikasi lain.

## Demo yang masih dibutuhkan

Pane belum diuji pada Hermes Desktop sungguhan. Tes kontrak JavaScript memeriksa normalisasi event, bukan tampilan UI live. Rekam video dari runtime nyata di bawah 90 detik, tunjukkan aktivitas tool/rekomendasi/guard, tag `@NousResearch`, dan sertakan screenshot asli di PR. Jangan gunakan mock UI sebagai bukti integrasi. [5]

Tenggat pengumuman: **5:00 PM Eastern, 11 November 2026**, setara **5:00 pagi WIB, 12 November 2026**. Setelah PR katalog disinkronkan dan demo X siap, masukkan kedua tautan melalui form resmi. Audit teknis dan validasi tidak menjamin kemenangan kontes. [1]

## Referensi

[1]: https://x.com/NousResearch/status/2118094256438936062 "Pengumuman resmi Hermes Agent Plugin Hackathon"
[2]: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission "Aturan submission katalog Hermes"
[3]: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins "Panduan pengembangan plugin Hermes dan penyimpanan state"
[4]: https://raw.githubusercontent.com/NousResearch/hermes-agent/v0.22.6/plugins/plugin_storage.py "API plugin_data_dir pada Hermes v0.22.6"
[5]: https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk "Panduan Hermes Desktop Plugin SDK"
[6]: https://github.com/NousResearch/hermes-agent/pull/151221 "PR katalog resmi Rariflat"

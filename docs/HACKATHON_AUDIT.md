# Audit kesiapan Hermes Plugin Hackathon — Rariflat

## Kesimpulan

Rariflat sudah memiliki lebih dari sekadar prompt atau skill: plugin mendaftarkan tools, hooks, guard opsional, dan pane Desktop; itu cocok dengan preferensi juri terhadap plugin yang melakukan pekerjaan nyata. Kontes menilai usefulness, reliability, polish, dan creativity. Submission wajib mencakup PR ke katalog resmi Hermes, video demo di X yang berdurasi di bawah 90 detik dan menandai `@NousResearch`, serta pengisian form dengan kedua tautan sebelum 5 PM Eastern, 11 November 2026—setara 5 AM WIB, 12 November 2026. [1]

## Status PR dan sumber

PR katalog resmi [`NousResearch/hermes-agent#151221`](https://github.com/NousResearch/hermes-agent/pull/151221) memang sudah ada; koreksi dari dugaan awal audit: PR #7 yang Anda kirim bukan satu-satunya PR terkait. #151221 menambahkan entry katalog komunitas dan mem-pin source SHA `950796253faa2d9b69c3c2d1256924d18ae03e9c`. Halaman PR menyatakan workflow katalog berstatus `action_required`, sehingga validasi katalog pada SHA tersebut belum dijalankan dan memerlukan persetujuan maintainer. [2]

PR repo Anda [`rariflat-hermes#7`](https://github.com/wadezigh96/rariflat-hermes/pull/7) sudah di-squash-merge ke `main` sebagai commit `78a76ff`; semua check yang terlihat sebelum merge lulus. PR tersebut memperbaiki contoh install dan validasi Hermes, tetapi bukan PR penambahan entry ke `NousResearch/hermes-agent`. [3]

Ada ketidaksamaan pin yang perlu ditutup sebelum rilis. Sebelum PR #7 di-merge, draft `plugin-catalog/rariflat.yaml` mem-pin `1954ef...` dan quickstart mem-pin `6bbcfa...`, sedangkan PR #151221 mem-pin `950796...`. PR #7 menyamakan quickstart ke `950796...`, tetapi draft YAML di `main` masih tertinggal. Commit source `950796...` lebih lama dari code HEAD `9dcf078...` yang diaudit; merge docs menghasilkan `78a76ff` tanpa mengubah source. Saya membuat commit kode baru `31c522ddccd32674a474bf8b73273b4605e14b2e` di branch `fix/hackathon-readiness`; README, quickstart, dan draft YAML pada branch ini kini mem-pin commit kode tersebut. Setelah branch dipush, entry pada PR #151221 masih harus diperbarui ke SHA yang sama. Pin harus menunjuk tepat ke source yang divalidasi. [2] [4] [5] [6] [7] [8] [9]

## Perbaikan yang saya terapkan di working copy

- Guard kini menyimpan pilihan ON/OFF secara lokal dan tetap menghormati `RARIFLAT_GUARD` bila variabel itu sengaja diatur saat startup.
- `RARIFLAT_COOLDOWN=0` kini memulihkan streak pada pemanggilan berikutnya, bukan membuat blokir terus-menerus.
- Hasil error mentah tidak lagi dikirim ke event Desktop; pane menerima alasan umum agar error yang memuat token atau data pengguna tidak ikut ditampilkan.
- `RARIFLAT_LEARN_ARGS=0` kini benar-benar menghentikan penambahan token dari argumen tool, sesuai dokumentasi privasi.
- Installer tidak lagi bergantung pada `rsync` dan menyalin `event-contract.mjs` yang dibutuhkan pane Desktop. Tes smoke installer ditambahkan ke CI.
- Checklist submission dan demo script diperbaiki. Demo tidak lagi menyebut perintah `/rariflat explain` atau countdown cooldown yang tidak tersedia.

## Hasil validasi

Pada source yang akan dipublish: 37 tes Python lulus, 2 tes Node lulus, installer smoke test lulus, `git diff --check` bersih, dan Hermes Agent v0.23.0 meluluskan `hermes plugins validate . --install-deps` serta `hermes plugins doctor .`. SHA `950796...` yang saat ini dipin PR #151221 juga lulus validator lokal dan Plugin Doctor. Security scan dan pemeriksaan Desktop surface lulus. Ini belum menggantikan workflow katalog resmi yang masih `action_required`, dan tidak membuktikan pane berjalan pada sesi Hermes Desktop sungguhan; rekaman layar dan screenshot harus diambil dari runtime yang benar.

## Yang masih harus dilakukan

1. Push branch perubahan dan pastikan commit source `31c522d` tersedia publik; pin lokal sudah diarahkan ke SHA tersebut.
2. Minta maintainer Hermes menyetujui workflow PR #151221 yang berstatus `action_required`, lalu tangani hasil validasi katalog sampai hijau.
3. Uji pane secara langsung di Hermes Desktop dan ambil screenshot nyata untuk PR katalog.
4. Rekam demo yang menunjukkan aktivitas tool, hasil rekomendasi, dan guard benar-benar memblokir panggilan. Tautan X yang Anda berikan (`Time to cook`) bukan video demo; posting demo terpisah dan tag `@NousResearch`.
5. Kirim tautan PR katalog resmi dan tautan demo X melalui Typeform sebelum tenggat.

Audit teknis dan tes yang lulus tidak menjamin kemenangan; hasil akhir juga bergantung pada review maintainer dan demo nyata yang memperlihatkan fitur bekerja.

## Referensi

[1]: https://x.com/NousResearch/status/2118094256438936062 "Pengumuman resmi Hermes Agent Plugin Hackathon"
[2]: https://github.com/NousResearch/hermes-agent/pull/151221 "PR katalog resmi Rariflat"
[3]: https://github.com/wadezigh96/rariflat-hermes/pull/7 "PR dokumentasi Rariflat nomor 7"
[4]: https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission "Panduan submission katalog Hermes"
[5]: https://github.com/wadezigh96/rariflat-hermes/commit/9dcf078d62fea5ee7bd43620db44e187c1a44af5 "Commit main Rariflat yang diaudit"
[6]: https://github.com/wadezigh96/rariflat-hermes/commit/950796253faa2d9b69c3c2d1256924d18ae03e9c "Commit source yang dipin PR katalog"
[7]: https://raw.githubusercontent.com/wadezigh96/rariflat-hermes/main/plugin-catalog/rariflat.yaml "Draft catalog YAML pada main sebelum audit"
[8]: https://raw.githubusercontent.com/wadezigh96/rariflat-hermes/main/docs/QUICKSTART_AND_USE_CASES.md "Quickstart pada main sebelum audit"
[9]: https://github.com/wadezigh96/rariflat-hermes/commit/31c522ddccd32674a474bf8b73273b4605e14b2e "Commit kode perbaikan hackathon"

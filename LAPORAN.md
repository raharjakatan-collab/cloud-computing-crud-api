# Laporan Praktikum CI/CD

**Nama:** Katan Raharja

**NIM:** 101012300394

**Repository:** https://github.com/raharjakatan-collab/cloud-computing-crud-api

## Ringkasan

| Tugas | Kondisi | Bukti |
| --- | --- | --- |
| A. Pipeline | Selesai | Build #3 sampai #5 sukses, `bukti/console-build-3.txt` |
| B. Webhook | Selesai | Build #4 dan #5 terpicu push, `bukti/jenkins-build-4-dari-webhook.jpg` |
| C. Persistensi | Selesai | Tiga pesan bertahan setelah redeploy Jenkins, `bukti/uji-setelah-jenkins.txt` |
| D. Pengembangan | Selesai, enam item | Lihat bagian Tugas D |

## Tugas A

Jenkins mengambil kode dari repository privat memakai credential `github-pat-readonly`. Tokennya berjenis Fine-grained, hanya untuk repository ini, dengan izin `Contents: Read-only` dan `Metadata: Read-only`.

Pipeline berisi enam stage:

1. Checkout kode
2. Pemeriksaan sintaks dengan `py_compile`
3. Test otomatis
4. Build image
5. Deployment ke `production-api-container`
6. Health check

Build #3 dijalankan dengan Build Now dan selesai `SUCCESS`, 12 test lulus. Image `python-crud-api:3`, `python-crud-api:16c6592`, dan `latest` terbentuk. Daftar build ada di `bukti/jenkins-daftar-build.jpg`.

## Tugas B

Tunnel ngrok meneruskan `https://spotted-breeching-although.ngrok-free.dev` ke Jenkins, dan webhook GitHub mengarah ke path `/github-webhook/` dengan event push saja.

Commit `313c0cc` di-push tanpa menekan Build Now. GitHub mencatat pengiriman sukses, log Jenkins menulis `Received PushEvent`, dan build #4 dimulai dengan keterangan `Started by GitHub push by raharjakatan-collab`. Push berikutnya memicu build #5 dengan cara yang sama. Riwayat pengiriman ada di `bukti/github-recent-deliveries.jpg`. Delivery push untuk build #5 dibalas HTTP 200 dalam 0,68 detik, seperti terlihat pada `bukti/github-response-200.jpg`.

ngrok dijalankan dari image Docker resmi `ngrok/ngrok`, bukan dari agent Windows. Alasannya ada di bagian Masalah yang ditemui. Tunnel sudah dihentikan sebelum pengujian rollback, jadi build #7 sampai #10 dijalankan lewat Jenkins secara manual, bukan oleh webhook.

## Uji endpoint

Tabel ini berasal dari deploy manual commit `4fb1ce6`, dengan log di `bukti/hasil-uji-lokal.txt`. Health, input kosong, dan delete index tidak ada diuji ulang pada container hasil deploy Jenkins, dengan hasil yang sama.

| Permintaan | Hasil |
| --- | --- |
| `GET /health` | 200 |
| `GET /messages` awal | 200, total 0 |
| `POST /messages` | 201 |
| `POST` pesan kosong | 400 |
| `GET /messages/1` | 200 |
| `DELETE /messages?index=2` | 200 |
| `DELETE /messages?index=999` | 404 |

## Tugas C

Tiga pesan tersimpan sebelum build #5: dua dari uji awal dan satu pesan `Pesan dibuat sebelum redeploy Jenkins`. Build #5 mengganti container dari `f828aa9f143d` menjadi `8843b391f34b`, dan `GET /messages` tetap mengembalikan ketiganya dengan nilai `created_at` yang sama persis.

Container adalah proses dengan lapisan tulis sementara, dan lapisan itu lenyap ketika container dihapus. Named volume adalah penyimpanan terpisah yang dikelola Docker. Karena `messages.json` berada di volume, mengganti container tidak menyentuh datanya.

## Tugas D

**Endpoint satu pesan.** `GET /messages/{index}` menjawab 200, atau 404 bila index tidak ada, atau 400 bila bukan angka.

**Test otomatis.** Dua belas test di `tests/test_api.py` memakai server sementara, sehingga data asli aman. Stage test berada sebelum build agar kode rusak berhenti lebih awal.

**Docker `HEALTHCHECK`.** Docker memanggil `/health` tiap 10 detik memakai Python, karena image slim tidak berisi curl. Hasil pengujian: `healthy`. Bedanya dengan health check Jenkins:

| | `HEALTHCHECK` | Jenkins |
| --- | --- | --- |
| Lokasi | Di dalam container | Di luar container |
| Frekuensi | Terus-menerus | Sekali per deploy |
| Dampak gagal | Status `unhealthy` | Build gagal |

**Tag commit SHA.** Image `python-crud-api:313c0cc` menunjuk langsung ke kode sumbernya, jadi tag tetap bermakna walau riwayat build Jenkins dibersihkan. Sejak build #7, container dijalankan dari tag SHA, bukan `latest`.

**Rollback otomatis.** Sebelum container lama dihentikan, image yang sedang berjalan diberi tag `python-crud-api:previous`. Jika pipeline gagal setelah deploy, blok `post { failure }` menjalankan ulang image itu dan memeriksa `/health`. Jika kegagalan terjadi sebelum deploy, container produksi tidak disentuh.

**Rollback manual.** Parameter `ROLLBACK_TO` diisi tag image lama lewat Build with Parameters. Tahap sintaks, test, dan build dilewati, lalu tag tersebut langsung dideploy. Tag yang tidak ada akan gagal lebih dulu pada `docker image inspect`, sebelum container lama dihentikan.

| Build | Commit atau parameter | Hasil | Status |
| --- | --- | --- | --- |
| #7 | `e437bcf`, rollback ditambahkan | Container berjalan dari tag SHA | SUCCESS |
| #8 | `de0d60e`, port sengaja diubah ke 5001 | Test dan build lolos, health check gagal 10 kali, rollback berhasil | FAILURE |
| #9 | `20d985f`, port dikembalikan ke 5000 | Deployment dan health check berhasil | SUCCESS |
| #10 | `ROLLBACK_TO=e437bcf` | Tiga tahap dilewati, image `e437bcf` berjalan dalam 8,8 detik | SUCCESS |

Build #8 tetap berstatus FAILURE karena versi baru memang rusak. Layanan kembali sehat lewat `python-crud-api:previous`, dan `GET /messages` tetap mengembalikan 3 pesan setelah build #8 dan #10.

## Masalah yang ditemui

**Jenkins tidak bisa memakai Docker.** `docker ps` dari `jenkins-server` gagal dengan `permission denied` karena socket hanya dapat diakses `root`, sedangkan Jenkins berjalan sebagai user `jenkins`. Perbaikannya adalah `chgrp jenkins` pada socket. Perubahan ini perlu diulang jika Docker Desktop dimulai ulang.

**ngrok Windows tidak bisa dipakai.** Versi dari winget, 3.3.1, ditolak karena akun butuh minimal 3.28.0. Setelah `ngrok update` ke 3.39.13, Windows Defender menandai file itu sebagai `Trojan:Win32/Kepavll!rfn` dan memblokirnya. Hasil deteksi ini tidak diverifikasi lebih lanjut dan Defender tidak diubah. Tunnel dijalankan dari image Docker resmi di network `jenkins-net`, dengan target `jenkins-server:8080`.

**Token sempat muncul di chat.** Token GitHub pertama dihapus dan diganti token baru yang langsung disimpan di Jenkins Credentials, sesuai aturan pada bagian 5.4 panduan.

**Health check `localhost` tidak bisa dipakai.** Panduan memakai `curl http://localhost:5000/health`, padahal perintah itu berjalan di dalam container Jenkins, tempat tidak ada API. Solusinya, API dipasang ke network `jenkins-net` dan dipanggil dengan nama container, ditambah percobaan ulang karena API butuh beberapa detik untuk siap.

## Analisis

**Alur `git push` hingga container baru.** Push diterima GitHub, lalu webhook dikirim ke domain ngrok. Tunnel meneruskannya ke Jenkins, yang mencocokkan repository dengan job dan memulai pipeline. Setelah kode lolos pemeriksaan, image dibangun, container diganti, dan health check memastikan layanan hidup.

**PAT, webhook secret, dan authtoken.** Ketiganya membuktikan identitas pada tiga hubungan berbeda. PAT untuk Jenkins ke GitHub, webhook secret untuk GitHub ke Jenkins, dan authtoken untuk agent ngrok ke layanan ngrok.

**PAT read-only.** Pipeline hanya mengunduh kode, yang tercakup izin baca. Push menulis ke repository sehingga butuh izin tulis, dan token ini sengaja tidak memilikinya.

**Risiko Docker socket.** Akses ke socket berarti kendali penuh atas Docker daemon. Pemiliknya dapat menjalankan container yang memasang filesystem host, sehingga nilainya setara root di host.

**URL ngrok berubah.** Webhook menyimpan satu alamat tetap. Alamat baru dari ngrok tidak diketahui GitHub, jadi event terus dikirim ke tujuan yang tidak lagi ada.

**Named volume bertahan.** Volume tidak dimiliki container. Menghapus container hanya melepas kaitannya, dan isi volume hilang hanya lewat `docker volume rm`.

**CI dan CD.** CI mencakup sintaks, test, dan build, yaitu tahap yang menilai perubahan. CD mencakup deployment dan health check, yaitu tahap yang menerapkan perubahan ke layanan.

**Deploy sukses, health check gagal.** Build dibiarkan gagal, dan layanan dipulihkan dengan image sebelumnya. Pipeline ini melakukannya otomatis, seperti terbukti pada build #8. Setelah itu baca `docker logs` dari versi yang gagal, lalu perbaiki penyebabnya lewat commit baru.

## Daftar bukti

| Bukti | File |
| --- | --- |
| Daftar build sukses | `bukti/jenkins-daftar-build.jpg` |
| Console Output | `bukti/console-build-3.txt`, `-4.txt`, `-5.txt` |
| Recent Deliveries webhook | `bukti/github-recent-deliveries.jpg`, `bukti/github-response-200.jpg` |
| Build dari push | `bukti/jenkins-build-4-dari-webhook.jpg` |
| Output curl health dan CRUD | `bukti/hasil-uji-lokal.txt`, `bukti/uji-setelah-jenkins.txt` |
| Persistensi setelah redeploy | `bukti/uji-setelah-jenkins.txt` |
| Rollback otomatis | `bukti/console-build-8.txt` |
| Rollback manual | `bukti/console-build-10.txt`, `bukti/jenkins-rollback-manual.jpg`, `bukti/jenkins-build-10-rollback.jpg` |
| Daftar build dengan rollback | `bukti/jenkins-daftar-build-rollback.jpg` |

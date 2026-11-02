# Laporan Praktikum CI/CD

**Repository:** https://github.com/raharjakatan-collab/cloud-computing-crud-api

## Ringkasan

| Tugas | Kondisi | Bukti |
| --- | --- | --- |
| A. Pipeline | Kode lengkap, belum berjalan di Jenkins | Perintah pipeline lolos di luar Jenkins |
| B. Webhook | Belum dikerjakan | Butuh login GitHub dan authtoken ngrok |
| C. Persistensi | Terbukti di luar Jenkins | Dua pesan bertahan setelah redeploy |
| D. Pengembangan | Selesai, empat item | Lihat bagian Tugas D |

Semua angka di bawah berasal dari commit `4fb1ce6`, dengan log lengkap di `bukti/hasil-uji-lokal.txt`. Perintah `sh` pada `Jenkinsfile` dijalankan di container sementara dari image Jenkins, jadi hasil ini bukan build Jenkins.

## Tugas A

Pipeline berisi enam stage:

1. Checkout kode
2. Pemeriksaan sintaks dengan `py_compile`
3. Test otomatis
4. Build image
5. Deployment ke `production-api-container`
6. Health check

Dua putaran pipeline selesai dengan exit code 0 dan 12 test lulus pada keduanya.

## Uji endpoint

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

Dua pesan disimpan, lalu pipeline dijalankan lagi. ID container berubah dari `b84a067799a1` menjadi `fde1193dd8e4`, sementara kedua pesan kembali dengan nilai `created_at` yang sama persis.

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

**Tag commit SHA.** Image `python-crud-api:4fb1ce6` menunjuk langsung ke kode sumbernya, jadi tag tetap bermakna walau riwayat build Jenkins dibersihkan.

## Masalah yang ditemui

**Jenkins tidak bisa memakai Docker.** `docker ps` dari `jenkins-server` gagal dengan `permission denied` karena socket hanya dapat diakses `root`, sedangkan Jenkins berjalan sebagai user `jenkins`. Masalah ini belum diperbaiki. Perbaikannya adalah `chgrp jenkins` pada socket, dan pipeline Jenkins tidak akan berjalan sebelum itu.

**Health check `localhost` tidak bisa dipakai.** Panduan memakai `curl http://localhost:5000/health`, padahal perintah itu berjalan di dalam container Jenkins, tempat tidak ada API. Solusinya, API dipasang ke network `jenkins-net` dan dipanggil dengan nama container, ditambah percobaan ulang karena API butuh beberapa detik untuk siap.

## Analisis

**Alur `git push` hingga container baru.** Push diterima GitHub, lalu webhook dikirim ke domain ngrok. Tunnel meneruskannya ke Jenkins, yang mencocokkan repository dengan job dan memulai pipeline. Setelah kode lolos pemeriksaan, image dibangun, container diganti, dan health check memastikan layanan hidup.

**PAT, webhook secret, dan authtoken.** Ketiganya membuktikan identitas pada tiga hubungan berbeda. PAT untuk Jenkins ke GitHub, webhook secret untuk GitHub ke Jenkins, dan authtoken untuk agent ngrok ke layanan ngrok.

**PAT read-only.** Pipeline hanya mengunduh kode, yang tercakup izin baca. Push menulis ke repository sehingga butuh izin tulis, dan token ini sengaja tidak memilikinya.

**Risiko Docker socket.** Akses ke socket berarti kendali penuh atas Docker daemon. Pemiliknya dapat menjalankan container yang memasang filesystem host, sehingga nilainya setara root di host.

**URL ngrok berubah.** Webhook menyimpan satu alamat tetap. Alamat baru dari ngrok tidak diketahui GitHub, jadi event terus dikirim ke tujuan yang tidak lagi ada.

**Named volume bertahan.** Volume tidak dimiliki container. Menghapus container hanya melepas kaitannya, dan isi volume hilang hanya lewat `docker volume rm`.

**CI dan CD.** CI mencakup sintaks, test, dan build, yaitu tahap yang menilai perubahan. CD mencakup deployment dan health check, yaitu tahap yang menerapkan perubahan ke layanan.

**Deploy sukses, health check gagal.** Biarkan build berstatus gagal, baca log container, lalu jalankan image dari tag sebelumnya dengan volume yang sama. Setelah layanan pulih, perbaiki penyebabnya lewat commit baru.

## Bukti yang masih harus dikumpulkan

- [ ] Screenshot build sukses dan Console Output Jenkins
- [ ] Recent Deliveries webhook GitHub
- [ ] Build yang terpicu oleh push
- [ ] Redeploy lewat Jenkins dengan data tetap ada

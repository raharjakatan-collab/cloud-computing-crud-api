# Python CRUD API

REST API berbasis Python standard library. Jenkins mengujinya, membangun image Docker, lalu menggantinya di container yang berjalan. Pesan disimpan di Docker named volume, jadi tidak hilang saat container diganti.

## Endpoint

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/health` | Status layanan |
| GET | `/messages` | Semua pesan |
| GET | `/messages/{index}` | Satu pesan |
| POST | `/messages` | Tambah pesan, body `{"message": "..."}` |
| DELETE | `/messages?index={index}` | Hapus pesan |

## Menjalankan

```bash
docker build -t python-crud-api:manual .
docker run -d --name production-api-container -p 5000:5000 \
  -v production-api-data:/var/lib/backend_data python-crud-api:manual
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Pipeline

`Jenkinsfile` menjalankan checkout, syntax check, test, build image, deploy, dan health check. Image diberi tag nomor build, commit SHA, dan `latest`.

Jenkins berjalan di container memakai image dari `Dockerfile.jenkins` dan memasang Docker socket host, sehingga konfigurasi ini hanya untuk mesin lab. Token disimpan di Jenkins Credentials dengan ID `github-pat-readonly`, tidak pernah di repository.

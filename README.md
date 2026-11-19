# İbnüssebil

**Excel’den sâikin telefonuna, beş dakikada.**

İbnüssebil, küçük filolar için sade bir sevkiyat ve güzergâh uygulamasıdır:

- Kervanbaşı Excel’den menzilleri irsal eder.
- Sâikleri seçer, OR-Tools ile güzergâhları oluşturur.
- Güzergâhı yola çıkarır.
- Sâik uygulama indirmeden, tarayıcıdan kendi seferini görür ve menzilleri işler.

Bu klasör, mevcut büyük monorepo’dan bağımsız, kasıtlı olarak küçük tutulmuş **v1** uygulamasıdır.

Kısa lügat: **Sâik** = sürücü, **Menzil** = durak, **Sevkiyat** = sevk, **Nümune** = şablon, **İrsal** = içe aktarma, **Yola çıkarma** = yayınlama.

## Hızlı başlangıç

```bash
cd ibnussebil
bash run.sh
```

Aç:

- Web: http://localhost:5173
- API: http://127.0.0.1:8000/docs

İlk çalıştırmada demo verisi ve hesaplar oluşturulur.

### Demo hesapları

| Rol | Telefon | Şifre |
|---|---|---|
| Kervanbaşı | `05001112233` | `demo1234` |
| Sâik (sürücü) | `05002223344` | `demo1234` |
| Sâik 2 (sürücü) | `05003334455` | `demo1234` |

Demo verisini sıfırlamak için:

```bash
cd api
.venv/bin/python -m app.seed_demo --reset
```

## Docker ile çalıştırma

```bash
cd ibnussebil
JWT_SECRET="uzun-rastgele-bir-anahtar" docker compose up --build
```

Aç: http://localhost:8000

Docker imajı web arayüzünü de derler; FastAPI aynı porttan hem API’yi hem SPA’yı sunar.

## Mülakat Notları

CV’deki AWS/Lambda, MongoDB, TypeScript/Node, event-driven ve last-mile konularına göre 23 detaylı teknik soru ve cevap:

- [Backend Mülakat Notları — PDF](docs/interview-notes.pdf)
- [Backend Mülakat Notları — HTML kaynak](docs/interview-notes.html)

## Teknik 101

Bir web sitesinin canlıda nasıl ayakta durduğunu anlatan şemalı PDF:

- [Web Sitesi 101 — PDF](docs/web-101.pdf)
- [Web Sitesi 101 — HTML kaynak](docs/web-101.html)

## Canlıya çıkış

Domain, VPS, DNS, HTTPS, yedekleme ve demo reset dahil adım adım rehber:

- [DEPLOY.md](DEPLOY.md)
- `docker-compose.prod.yml`
- `Caddyfile`
- `.env.production.example`
- `scripts/backup.sh`
- `scripts/deploy.sh`

## Ne var?

### Kervanbaşı

- **Sevkiyat** sayfası: Excel nümunesi indirme, `.xlsx` irsal, önizleme, hatalı satırları görme, menzilleri içeri alma.
- **Elle menzil ekleme:** adres, alıcı, telefon, zaman penceresi, ağırlık ve not ile tek menzil; adres yoksa koordinat, koordinat yoksa otomatik geocoding.
- Sâik seçimi ve OR-Tools ile güzergâh oluşturma.
- **Taslak güzergâhta elle müdahale:** menzilleri yukarı/aşağı sıralama, güzergâhtan çıkarma, sevkiyat bekleyen menzili güzergâha ekleme.
- Taslak güzergâhı haritada inceleme, yola çıkarma, taslağa alma, silme.
- **Seferler** sayfası: günün tüm güzergâhları ve ilerleme.
- **Kervan** sayfası: davet kodu, üyeler, rol değiştirme, üye çıkarma, depo/vardiya ayarları.
- **Künye** sayfası: ad güncelleme, şifre değiştirme, kafile.

### Sâik

- Davet koduyla kervana katılma.
- **Seferim** sayfası: yalnızca kendi yola çıkarılmış güzergâhı.
- Harita, sıralı menziller, tahmini varış, telefonla arama, Google Maps yol tarifi.
- Teslim edildi / teslim edilemedi + neden + not.
- **Künye** sayfası: kervan, rol, kafile, şifre değiştirme.

### Roller ve güvenlik

- Davet kodu **yalnızca sâik** olarak katılma sağlar. Kervanbaşı yetkisi koddan gelmez.
- Sâik yalnızca kendi güzergâhını görür; API bunu sunucu tarafında doğrular.
- Rol değiştirme yalnızca kervanbaşına açıktır.
- Son kervanbaşı sâik yapılamaz; kervan sahibi çıkarılamaz.
- Aktif seferi olan sâik çıkarılamaz veya kervandan ayrılamaz.
- Davet kodu yenilenebilir, süresi ve kullanım limiti vardır.
- Şifreler bcrypt ile saklanır; oturumlar JWT ile taşınır.

## Excel nümunesi

Sütunlar:

```text
menzil_id | alici_adi | telefon | adres | enlem | boylam |
baslangic_saat | bitis_saat | agirlik_kg | notlar
```

- `menzil_id` zorunlu ve kervan içinde benzersiz. Eski dosyalardaki `durak_id` de kabul edilir.
- `adres` zorunlu.
- `enlem/boylam` varsa adres çözümleme atlanır.
- Yoksa ücretsiz Photon servisi denenir.
- Saatler `HH:MM`.
- En fazla 1.000 satır.

Önizleme ekranında geçerli/hatalı satırlar ve hata CSV’si indirilebilir. Aynı `menzil_id` ikinci kez irsal edilmez.

## Mimari

```text
React + Vite + TypeScript + Leaflet
                │
                ▼
FastAPI + SQLAlchemy + SQLite
                │
      ┌─────────┴──────────┐
      ▼                    ▼
 OR-Tools CVRP        Photon (optional)
      │
      ▼
 Haversine fallback or OSRM (optional)
```

- **Optimizasyon:** OR-Tools, tek depo, teslimat menzilleri, sâik başına menzil limiti, vardiya bitişi, hizmet süresi ve isteğe bağlı zaman pencereleri.
- **Mesafe/süre:** `OSRM_BASE_URL` boşsa Haversine + şehir içi hız tahmini kullanılır. Doluysa OSRM Table API kullanılır.
- **Harita çizgisi:** Varsayılan olarak `https://router.project-osrm.org` üzerinden gerçek yol geometrisi alınır; çizgi boğazdan kuş uçuşu değil, köprü/karayolu üzerinden gider. `OSRM_BASE_URL` doluysa önce o kullanılır. Erişim yoksa düz çizgiye düşer.
- **Harita:** OpenStreetMap tile’ları; API anahtarı gerekmez.
- **Veritabanı:** v1 için SQLite. Pilot öncesi Postgres’e geçilebilir.

## Ücretli servis gerekir mi?

**v1 için hayır.**

- OR-Tools: açık kaynak
- SQLite: yerel dosya
- OpenStreetMap tile’ları: ücretsiz
- Photon: ücretsiz genel servis (üretimde kendi sunucunuz veya Google Geocoding önerilir)
- OSRM: opsiyonel, kendi sunucunuzda ücretsiz
- Public OSRM demo sunucusu: harita çizgisi için varsayılan, ücretsiz ama üretim için uygun değil

Üretime çıkarken önerilenler:

- Alan adı + HTTPS (Caddy / Cloudflare)
- Yönetilen Postgres
- Kendi OSRM sunucunuz veya OSRM barındırma (`OSRM_BASE_URL` ayarlayın)
- Sentry (opsiyonel)
- Yedekleme
- Google Geocoding veya Photon self-host

## Testler

```bash
cd api
.venv/bin/pytest -q
```

Testler şunları kapsar: kervan kurma, sâik katılımı, Excel önizleme/irsal, optimizasyon, yola çıkarma, sâik durum güncellemesi, rol değiştirme ve yetki kontrolleri.

## v1’de bilerek yok

- Mobil uygulama (web sâik sayfası yeterli)
- Canlı GPS / ETA
- Müşteri takip linki
- Fotoğraf/imza POD
- SMS/e-posta bildirimi
- Çoklu depo
- Araç ağırlık/hacim kapasitesi (şimdilik sâik başına menzil limiti)
- Faturalama
- Self-servis abonelik

## Sonraki adımlar

1. Gerçek bir günlük veriyle benchmark: OR-Tools rotası vs mevcut insan planı.
2. Pilot: tek depo, 3–10 sâik, bir hafta.
3. Sâik geri bildirimiyle PWA/offline kuyruk.
4. POD (fotoğraf/imza) ve müşteri takip linki.
5. Postgres + yönetilen dağıtım.
6. Acil/öncelikli menziller için otomatik öncelik puanı ve canlı yeniden sıralama.

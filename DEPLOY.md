# İbnüssebil — Canlıya Çıkış Rehberi

Bu rehber, `ibnussebil.com` üzerinde v1’i yayına almak için minimum adımları içerir.

## 0. Ne gerekiyor?

| İhtiyaç | Öneri | Yaklaşık maliyet |
|---|---|---|
| Domain | `ibnussebil.com` | $10–15 / yıl |
| VPS | Ubuntu 24.04, 4 vCPU / 8 GB RAM | €6–15 / ay |
| DNS / CDN | Cloudflare (ücretsiz plan) | $0 |
| HTTPS | Caddy (otomatik Let’s Encrypt) | $0 |
| Veritabanı | v1 için SQLite dosyası | $0 |
| Yedek | Sunucu dışına kopya (R2/S3/scp) | $0–5 / ay |

**Zorunlu ücretli şeyler:** domain + VPS. Başka subscription gerekmiyor.

> Not: Şu an uygulama SQLite kullanıyor. Ayrı bir MySQL/Postgres sunucusu **şart değil**. Ama yedek alınmazsa veri kaybolur.

---

## 1. Domain almak

Önerilen yerler:

1. **Cloudflare Registrar** — maliyetine yakın fiyat, gizlilik ücretsiz, DNS entegre.
2. **Porkbun** — uygun fiyat, ücretsiz WHOIS gizliliği.
3. **Namecheap** — kolay arayüz, ücretsiz WHOIS gizliliği.

### Cloudflare ile alma

1. https://dash.cloudflare.com → hesap aç.
2. **Domain Registration → Register Domains**.
3. `ibnussebil.com` ara ve satın al.
4. Cloudflare, domaini otomatik olarak kendi DNS’ine bağlar.
5. DNS kayıtlarını 4. adımda ekleyeceğiz.

### Başka yerden aldıysan

1. Cloudflare’e domaini ekle.
2. Cloudflare’in verdiği nameserver’ları registrar paneline yaz.
3. 5–30 dakika bekle.

---

## 2. VPS almak

Öneri: **Hetzner Cloud** (ucuz ve stabil) veya DigitalOcean.

- Hetzner: `CPX31` veya `CX32` (4 vCPU / 8 GB RAM)
- Lokasyon: Nuremberg / Falkenstein (İstanbul’a yeterince yakın)
- Ubuntu 24.04 LTS
- SSH key ekle
- IPv4 public IP al

> 8 GB RAM, ileride kendi OSRM sunucusunu da çalıştırmak istersen rahat olur. Şimdiki uygulama için 4 GB de yeterli.

---

## 3. Sunucu hazırlığı

Sunucuya gir:

```bash
ssh root@SUNUCU_IP
```

Sistem güncelle:

```bash
apt update && apt upgrade -y
apt install -y curl git ufw sqlite3
```

Yeni kullanıcı oluştur:

```bash
adduser deploy
usermod -aG sudo deploy
rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
```

SSH anahtarını test et:

```bash
ssh deploy@SUNUCU_IP
```

Güvenlik duvarı:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

Docker kur:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker deploy
exit
```

Tekrar gir ve kontrol et:

```bash
ssh deploy@SUNUCU_IP
docker --version
docker compose version
```

SSH şifre girişini kapatmadan önce anahtarla giriş yaptığından emin ol. Sonra:

```bash
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl reload ssh
```

---

## 4. Kodu sunucuya taşıma

### Seçenek A — GitHub (önerilen)

Projeyi GitHub’a koy:

```bash
cd ibnussebil
git init
git add .
git commit -m "İbnüssebil v1"
```

GitHub’da private repo oluştur ve push et. Sonra sunucuda:

```bash
cd /opt
sudo mkdir ibnussebil
sudo chown deploy:deploy ibnussebil
git clone git@github.com:KULLANICI/ibnussebil.git
cd ibnussebil
```

### Seçenek B — rsync

```bash
rsync -av --exclude node_modules --exclude .venv --exclude data --exclude dist \
  ./ibnussebil/ deploy@SUNUCU_IP:/opt/ibnussebil/
```

---

## 5. Ortam değişkenleri

Sunucuda:

```bash
cd /opt/ibnussebil
cp .env.production.example .env
openssl rand -hex 32
nano .env
```

`.env` içine güçlü JWT secret yaz:

```env
JWT_SECRET=buraya_openssl_ciktisi
CORS_ORIGINS=https://ibnussebil.com
GEOCODING_ENABLED=true
ROUTE_GEOMETRY_BASE_URL=https://router.project-osrm.org
OSRM_BASE_URL=
```

> `JWT_SECRET` boş bırakılırsa uygulama güvenli kabul edilmez. Mutlaka doldur.

---

## 6. DNS kayıtları

Cloudflare DNS panelinde:

| Type | Name | Content | Proxy |
|---|---|---|---|
| A | `@` | SUNUCU_IP | DNS only |
| A | `www` | SUNUCU_IP | DNS only |

İlk aşamada **DNS only** kullan. Caddy Let’s Encrypt sertifikasını aldıktan sonra istersen Cloudflare proxy’yi açabilirsin; o zaman SSL/TLS modunu **Full (strict)** yapmalısın.

Kontrol:

```bash
dig +short ibnussebil.com
```

SUNUCU_IP dönmelidir.

---

## 7. Uygulamayı başlat

```bash
cd /opt/ibnussebil
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f app
```

Caddy ilk açılışta sertifika alır. 30–60 saniye bekle.

Kontrol:

```bash
curl https://ibnussebil.com/api/health
```

Beklenen:

```json
{"status":"ok","app":"Ibnussebil"}
```

Site: https://ibnussebil.com

---

## 8. Demo mu, gerçek pilot mu?

### Public demo

Demo hesaplarıyla yayına al:

```bash
docker compose -f docker-compose.prod.yml exec app python -m app.seed_demo --reset
```

Demo hesapları:

- Kervanbaşı: `05001112233 / demo1234`
- Sâik: `05002223344 / demo1234`
- Sâik 2: `05003334455 / demo1234`

Public demo’da herkes yazabildiği için günlük reset önerilir:

```bash
crontab -e
```

Ekle:

```cron
0 4 * * * cd /opt/ibnussebil && docker compose -f docker-compose.prod.yml exec -T app python -m app.seed_demo --reset
```

### Gerçek pilot

`seed_demo` çalıştırma. Kervanbaşını normal signup ile oluştur veya kontrollü bir hesapla başlat.

Güvenlik notu: v1’de dispatcher signup açıktır. Gerçek pilotta herkesin kervan kurmasını istemiyorsan signup’ı kapatmak için küçük bir env kontrolü eklemeliyiz.

---

## 9. Yedekleme

Script hazır:

```bash
cd /opt/ibnussebil
./scripts/backup.sh
```

Cron:

```bash
crontab -e
```

Ekle:

```cron
0 3 * * * /opt/ibnussebil/scripts/backup.sh
```

Yedekler `backups/` altında oluşur. **Sunucu dışına** da kopyala:

- Cloudflare R2
- AWS S3
- Başka bir sunucuya `scp`
- veya `rclone`

Sunucu dışı yedek yoksa yedek yok sayılır.

---

## 10. Güncelleme

Kod değişince:

```bash
cd /opt/ibnussebil
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Kontrol:

```bash
docker compose -f docker-compose.prod.yml ps
curl https://ibnussebil.com/api/health
```

---

## 11. İzleme

Minimum:

- UptimeRobot → `https://ibnussebil.com/api/health`
- Haftalık `docker compose logs` kontrolü
- Disk doluluk kontrolü: `df -h`

Sonra:

- Sentry
- Cloudflare Analytics
- Günlük yedek doğrulama

---

## 12. Postgres’e geçiş ne zaman?

SQLite şunlar için yeterli:

- demo
- ilk pilot
- düşük eşzamanlılık
- tek uvicorn worker

Postgres’e geç:

- birden fazla kervan/tenant
- yoğun eşzamanlı yazma
- yönetilen yedekleme
- ölçekleme

Geçiş için:

1. `requirements.txt` içine `psycopg[binary]` ekle.
2. Compose’a `postgres:16-alpine` servisi ekle.
3. `DATABASE_URL=postgresql+psycopg://...` yap.
4. Veriyi SQLite’tan Postgres’e taşı.
5. `pg_dump` ile yedekle.

O zamana kadar SQLite + günlük yedek yeterli.

---

## 13. OSRM notu

Şu an:

- Harita çizgisi: public OSRM (`router.project-osrm.org`)
- Optimizasyon matrisi: `OSRM_BASE_URL` boşsa Haversine tahmini

İlk demo için yeterli. Gerçek pilotta daha doğru süre/mesafe için kendi OSRM sunucunu kurup `OSRM_BASE_URL` ayarlamak daha iyi olur. Public OSRM üretim için uygun değildir.

---

## 14. Canlıya çıkış kontrol listesi

- [ ] Domain alındı
- [ ] VPS açıldı
- [ ] SSH key ile giriş çalışıyor
- [ ] UFW sadece 22/80/443 açık
- [ ] Docker kuruldu
- [ ] `.env` içinde güçlü `JWT_SECRET` var
- [ ] DNS A kayıtları doğru
- [ ] `https://ibnussebil.com/api/health` çalışıyor
- [ ] HTTPS sertifikası aktif
- [ ] Demo hesapları veya gerçek kervanbaşı hazır
- [ ] Günlük yedek cron’u çalışıyor
- [ ] Yedek sunucu dışına kopyalanıyor
- [ ] UptimeRobot izlemesi açık
- [ ] Public demo ise günlük reset cron’u açık
- [ ] Gerçek pilot ise public signup riski değerlendirildi

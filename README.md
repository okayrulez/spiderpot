# Spiderpot

Windows için üç masaüstü tuzağı, özelleştirilebilir kısayollar ve isteğe bağlı yerel kamera fotoğrafları.

## Windows x64 · 1.0.14 beta

[QR eşleştirmeli Windows kurucusunu indir](https://github.com/okayrulez/spiderpot/releases/download/v1.0.14-beta/Spiderpot-1.0.14-Setup.exe) · [Sürüm notları ve SHA-256](https://github.com/okayrulez/spiderpot/releases/tag/v1.0.14-beta)

Kurucuyu çalıştırın. Önceden kurduysanız güncel sürüm aynı Windows kullanıcısının ayarlarını devralır. İlk kurulumda tercihlerinizi seçip **Kaydet ve Devam Et** düğmesine basın.

### iPhone ile eşleştirme

1. iPhone’da TestFlight üzerinden Spiderpot’u kurun. İlk deneme için telefonu ve PC’yi aynı yerel ağa bağlayın.
2. Windows’ta saatin yanındaki gizli simgeleri açın. Spiderpot’un dairesel simgesine sağ tıklayıp **Dashboard aç → Telefon eşleştir** yolunu izleyin.
3. **Erişimi aç → QR oluştur** düğmelerine basın. iPhone’da **QR kodunu okut** ile iki dakika geçerli kodu tarayın ve **Bağlan**’a dokunun.
4. Canlı ekranı gördükten sonra fare ve klavye kullanmak isterseniz PC’de ilgili izni açın. Paylaşımı bitirmek için PC’de **Durdur**’a basın.

Ekran ve giriş verileri iki cihaz arasında doğrudan TLS üzerinden taşınır. Mobil veriden denemek için 1.0.14 ve sonrasında **Ev modeminde 15 dk dış erişim aç** seçeneği kullanılabilir. Genel IPv4 adresi ve süreli UPnP yönlendirmesi destekleyen modemlerde Spiderpot yönlendirmeyi açar ve bağlantı adresini yeni QR’a ekler. Windows güvenlik duvarının TCP bağlantısına izin vermesi gerekir. CGNAT veya çift NAT durumunda dışarıdan ulaşılabilen IPv6, önceden yapılandırılmış bir dış adres ya da iki cihazın da eriştiği özel ağ adresi gerekir.

## Modlar ve simge

| Varsayılan kısayol | İşlev |
| --- | --- |
| **Ctrl+1** | Seçtiğiniz fotoğrafı ekranlarda açar ve fare girişlerini engeller. |
| **Ctrl+2** | Siyah ekran açar ve fare girişlerini engeller. |
| **Ctrl+3** | Mevcut ekran görünümünü değiştirmeden fare tuzağını etkinleştirir. |
| **F12** | Tuzağı ve fotoğraf çekimini durdurur. |

Kısayollar ayarlardan değiştirilebilir. Üç modda da kamera seçeneği açıksa fare veya klavye etkinliği fotoğraf çekimini tetikleyebilir. Yazılan metin ve tuş geçmişi saklanmaz. Ctrl+3, özgün çekirdekteki mevcut ekran modudur; masaüstünün görüntüsünü kaydetmez.

Uygulama simgesi şeffaf köşeli daire ve beyaz çemberdir. Sistem tepsisinde **pasifken kırmızı**, **tuzak aktifken yeşil** görünür. Simgeye sağ tıklayarak Ayarlar, Fotoğraflar, Tuzağı durdur ve Sistemi Tamamen Kapat seçeneklerine erişebilirsiniz. Kurulumun sol panelinde Noir görseli korunur.

Bu uygulama Windows oturum kilidinin yerine geçmez. Ctrl+Alt+Del gibi Windows güvenli ekranlarını engellemez. Bilgisayar güvenliği için Windows'un kendi oturum kilidini kullanın.

## Kamera ve veriler

- İlk kurulumda kamera seçeneği işaretli gelir. Fotoğraf çekimi, ayarları kaydederken onay verdiğinizde etkinleşir.
- Bekleme sırasında kamera açılmaz. Mikrofon ve video kaydı yoktur.
- Etkinlik fotoğrafları Windows hesabına bağlı DPAPI ile şifrelenir. Uygulama fotoğrafları internete göndermez.
- Tepsi menüsündeki **Fotoğraflar** bölümünden önizleme, dışa aktarma ve silme yapılır. Dışa aktarılan JPEG şifrelenmez.
- Varsayılan saklama 7 gündür; 1–30 gün seçilebilir. Uygulama açıkken süresi dolan kayıtlar temizlenir.
- Güncelleme eski masaüstü `Spiderpot_Yakalananlar` klasörünü silmez ve eski JPEG'leri kendiliğinden içeri aktarmaz.

[Gizlilik politikası](store/privacy-tr.txt)

Yalnız yetkili olduğunuz cihazlarda kullanın. Kamera kaydına girecek kişileri bilgilendirin ve gerekli izinleri alın.

## Kaynaktan çalıştırma ve derleme

Windows x64 ve Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe tools\build_assets.py
.\.venv\Scripts\python.exe Spiderpot.py --configure
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\build_release.py
```

Çıktılar deponun bir üst dizinindeki `outputs` klasörüne yazılır. Derleme sırasında resmi Microsoft SDK BuildTools NuGet paketi indirilir; kurulan uygulama bağımlılık indirmez. Derleme günlüğü bir üst dizindeki `build` klasöründedir.

MSIX paketinde Store'da ayrılan kimlik ve yayıncı bilgileri kullanılmalıdır. Geliştirme kimliğiyle oluşturulan `Development.msix`, imzasız bir paketleme denemesidir; Microsoft Store'a gönderilmez ve normal kullanıcı kurulumu için önerilmez. EXE ve GitHub sürümü de Microsoft Store sertifikası almış değildir.

## 1.0.1

- Eski ve yeni sürümlerin birlikte çalışması giderildi; eski adlarla uyumlu tek-kopya kilidi eklendi.
- Sürümlü kalıcı kurulum ve tek otomatik başlangıç kaydı eklendi.
- Kırmızı/beyaz uygulama logosu ve aktifken yeşil tepsi simgesi korundu.
- Noir setup görseli korundu, yanıltıcı ilerleme çubuğu kaldırıldı.
- Çevrimdışı uygulama, kamera tercihi, şifreli kayıtlar ve fotoğraf yöneticisi eklendi.

Noir görselinin kaynak depoda bulunması, Microsoft Store dağıtım haklarının doğrulandığı anlamına gelmez. Store başvurusundan önce görsel hakları ayrıca değerlendirilmelidir.

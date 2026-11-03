# Spiderpot

Windows için üç masaüstü tuzağı, özelleştirilebilir kısayollar ve isteğe bağlı yerel kamera fotoğrafları.

## İndir ve kur

[Spiderpot 1.0.1 Windows x64 kurulumunu indir](https://github.com/okayrulez/spiderpot/releases/download/v1.0.1/Spiderpot-1.0.1-Setup.exe)

1. `Spiderpot-1.0.1-Setup.exe` dosyasını çalıştırın. Python kurulumu veya kurulum sırasında internet bağlantısı gerekmez.
2. Kurucu, mevcut kullanıcıdaki `Spiderpot_Sistem.exe` ve `Spiderpot.exe` sürümlerini kapatır. Eski `Spiderpot_App` / `Spiderpot` başlangıç kayıtlarını ve eski başlangıç kısayollarını devralır.
3. Fotoğrafınızı, kısayolları ve kamera tercihinizi seçip **Kaydet ve Başlat** düğmesine basın.

Uygulama `%LOCALAPPDATA%\Programs\Spiderpot\versions\1.0.1` altına yerleşir. Başlat menüsünde Spiderpot kısayolu oluşturulur. Otomatik başlangıç açıksa yalnız güncel sürüme yönelen tek kayıt tutulur. Eski başlangıç kayıtlarının ve kısayolların yedeği `%LOCALAPPDATA%\Spiderpot\migration-backups` altındadır. Önceden indirilmiş EXE dosyaları, fotoğraflar ve kullanıcı belgeleri silinmez.

[ZIP paketi](https://github.com/okayrulez/spiderpot/releases/download/v1.0.1/Spiderpot-1.0.1-x64-Portable.zip) de kullanılabilir: tamamını çıkarın, `Spiderpot.exe` dosyasını açın. **Kaydet ve Başlat**, aynı güncelleme işlemini yaparak kalıcı konuma kurar; çıkarılan ZIP klasörünü sonradan taşımanız başlangıcı bozmaz.

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

- Kamera varsayılan kapalıdır ve yalnız ayrı bilgilendirmeyi kabul ederek açılır.
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

Çıktılar deponun bir üst dizinindeki `outputs` klasörüne yazılır. Derleme sırasında resmi Microsoft SDK BuildTools NuGet paketi indirilir; kurulan uygulama bağımlılık indirmez. Derleme günlüğü bir üst dizindeki `work/store-build` klasöründedir.

MSIX paketinde Store'da ayrılan kimlik ve yayıncı bilgileri kullanılmalıdır. Geliştirme kimliğiyle oluşturulan `Development.msix`, imzasız bir paketleme denemesidir; Microsoft Store'a gönderilmez ve normal kullanıcı kurulumu için önerilmez. EXE ve GitHub sürümü de Microsoft Store sertifikası almış değildir.

## 1.0.1

- Eski ve yeni sürümlerin birlikte çalışması giderildi; eski adlarla uyumlu tek-kopya kilidi eklendi.
- Sürümlü kalıcı kurulum ve tek otomatik başlangıç kaydı eklendi.
- Kırmızı/beyaz uygulama logosu ve aktifken yeşil tepsi simgesi korundu.
- Noir setup görseli korundu, yanıltıcı ilerleme çubuğu kaldırıldı.
- Çevrimdışı uygulama, kamera tercihi, şifreli kayıtlar ve fotoğraf yöneticisi eklendi.

Noir görselinin kaynak depoda bulunması, Microsoft Store dağıtım haklarının doğrulandığı anlamına gelmez. Store başvurusundan önce görsel hakları ayrıca değerlendirilmelidir.

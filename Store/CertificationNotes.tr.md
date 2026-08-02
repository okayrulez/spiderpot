# Microsoft Store Sertifika Test Notları

## Uygulamanın amacı

Spiderpot, kullanıcının kendi Windows bilgisayarında etkinleştirdiği tam ekran
modları ve isteğe bağlı yerel kamera geri bildirimi sunan bir masaüstü yardımcı
uygulamasıdır. Ağ bağlantısı kurmaz ve fotoğrafları dışarı göndermez.

## İlk çalıştırma

1. Başlat menüsünden Spiderpot'u açın.
2. Kamera açıklamasını okuyun. Kamera onayı varsayılan olarak kapalıdır.
3. En az bir Ctrl+1 görseli seçin veya uygulamanın varsayılan görselini bırakın.
4. “Ayarları Kaydet ve Spiderpot'u Başlat” düğmesine basın.

## Test kısayolları

- `Ctrl+1`: Seçili görselleri tam ekran slayt olarak gösterir.
- `Ctrl+2`: Siyah ekran modunu açar.
- `Ctrl+3`: Masaüstünü görünür bırakan tuzak modunu açar.
- `F12`: Etkin tuzak modunu kapatır (Ayarlar ekranında değiştirilebilir).

Bir tuzak modu açıkken fare/klavye etkileşimi algılanır. Kamera onayı verilmişse
uygulama tek bir kamera karesi alır, “YAKALANDIN!” geri bildirimini yaklaşık üç
saniye gösterir ve görüntüyü yerel olarak kaydeder. Onay kapalıysa fotoğraf
çekilmez.

## Yerel dosyalar

- Yapılandırma: `%LOCALAPPDATA%\Spiderpot\config.json`
- Duvar kâğıtları: `%LOCALAPPDATA%\Spiderpot\Wallpapers`
- Fotoğraflar: `Masaüstü\Spiderpot_Yakalananlar`
- Hata günlüğü: öncelikle kullanıcının seçilebilir/yazılabilir yerel konumları

## Otomatik başlangıç

Paket `windows.startupTask` uzantısını kullanır. Kullanıcı uygulamayı en az bir kez
başlattıktan sonra Spiderpot Windows oturumu açıldığında başlayabilir. Kullanıcı
bunu Görev Yöneticisi > Başlangıç uygulamaları bölümünden kapatabilir.

## Ağ ve hesap

Uygulamada oturum açma, reklam, abonelik, telemetri, analiz SDK'sı veya ağ üzerinden
veri aktarımı yoktur.

## WACK statik tarama notu

Windows App Certification Kit'in “Blocked executables” isteğe bağlı testi,
PyInstaller ile paketlenen standart Python çalışma zamanındaki metinleri ve
`CreateProcessW` başvurusunu raporlayabilir. Spiderpot komut istemi, kayıt defteri
aracı, hata ayıklayıcı veya raporda adları geçen `cmd`, `reg`, `cdb`, `csi` ve
`dnx` programlarını çalıştırmaz. Uygulamanın oluşturduğu iki süreç de paketin
kendisinde bulunan `Spiderpot_Ayarlar.exe` ve `Spiderpot_Sistem.exe` dosyalarıdır.

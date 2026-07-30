# Spiderpot Gizlilik Politikası

Son güncelleme: 30 Temmuz 2026

Spiderpot, Windows bilgisayarında çalışan yerel bir ekran tuzağı ve masaüstü
yardımcı uygulamasıdır. Bu metin, uygulamanın kamera ve dosya kullanımını açıklar.

## Toplanan ve işlenen veriler

Spiderpot yalnızca kullanıcı aşağıdaki iki işlemi de gerçekleştirdiğinde kameradan
tek bir görüntü alabilir:

1. Ayarlar ekranında kamera özelliğine açıkça izin verir.
2. Bir tuzak modunu kendisi etkinleştirir ve bu mod açıkken fare veya klavye
   etkileşimi algılanır.

Kamera izni verilmezse ekran modları çalışmaya devam eder fakat fotoğraf çekilmez.
Uygulama ses kaydetmez, video kaydetmez, konum bilgisi toplamaz ve kullanıcı hesabı
oluşturmaz.

## Verilerin saklanması ve paylaşılması

Çekilen görüntüler yalnızca kullanıcının kendi bilgisayarındaki
`Masaüstü\Spiderpot_Yakalananlar` klasörüne kaydedilir. Ana konum kullanılamazsa
uygulama yerel bir yedek klasöre kaydetmeyi deneyebilir. Görüntüler Spiderpot
tarafından internete gönderilmez, bulut hizmetine yüklenmez, satılmaz ve üçüncü
taraflarla paylaşılmaz.

Ayarlar ve seçilen duvar kâğıtları `%LOCALAPPDATA%\Spiderpot` klasöründe yerel
olarak tutulur. Uygulamanın çalışması için bir çevrim içi hesaba gerek yoktur.

## Kullanıcının seçenekleri

Kamera özelliği Spiderpot Ayarlar ekranındaki onay kutusu kapatılıp ayarlar
kaydedilerek her zaman devre dışı bırakılabilir. Kullanıcı, çekilen fotoğrafları
ve yerel ayarları ilgili klasörlerden istediği zaman silebilir.

## Verilerin silinmesi

Spiderpot'un tuttuğu yerel verileri tamamen silmek için:

- `Masaüstü\Spiderpot_Yakalananlar` klasörünü silin.
- `%LOCALAPPDATA%\Spiderpot` klasörünü silin.

Uygulamanın kaldırılması bu kişisel klasörleri otomatik olarak silmeyebilir; bu
sayede kullanıcı fotoğraflarını yanlışlıkla kaybetmez.

## Çocukların gizliliği

Spiderpot çocuklara yönelik değildir ve bilerek çocuklardan kişisel veri toplamaz.

## İletişim

Gizlilik veya destek soruları için: `{{SUPPORT_EMAIL}}`

Yayıncı: `{{PUBLISHER_DISPLAY_NAME}}`


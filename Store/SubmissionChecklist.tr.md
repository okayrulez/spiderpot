# Spiderpot Microsoft Store Gönderim Kontrol Listesi

## Kod ve paket — tamamlandı

- [x] Python gerektirmeyen `Spiderpot_Sistem.exe` üretimi
- [x] Mağazadan açılabilen `Spiderpot_Ayarlar.exe` üretimi
- [x] Kamera özelliğinin varsayılan olarak kapalı olması
- [x] Kamera kullanımından önce açık onay ve yerel saklama açıklaması
- [x] Ayar ve duvar kâğıtlarının kullanıcı yazılabilir klasöründe saklanması
- [x] Kayıt defterinde yönetici düzeyi USB/cihaz politikası değiştiren kodun kaldırılması
- [x] MSIX manifestinde `runFullTrust`, `webcam` ve `windows.startupTask` bildirimleri
- [x] x64 MSIX paketi, logolar ve arşiv bütünlüğü doğrulaması
- [x] Store liste metni, gizlilik taslağı, yaş derecelendirme ve sertifika notları

## Partner Center'dan alınacak değerler

Ürün adı ayrıldıktan sonra Partner Center > Product identity sayfasındaki değerleri
`Store/store_identity.json` dosyasına aynen girin:

- `identity_name`: Package/Identity/Name
- `publisher`: Package/Identity/Publisher
- `publisher_display_name`: yayıncı görünen adı

Bu değerler gelmeden üretilen paket yalnızca teknik ön pakettir ve mağazaya
gönderilmemelidir.

## Son gönderim

- [ ] Ücretsiz Store geliştirici hesabı ve kimlik doğrulaması tamamlandı
- [ ] “Spiderpot” adı MSIX/PWA ürünü olarak ayrıldı
- [ ] Gerçek paket kimlik değerleri `store_identity.json` içine yazıldı
- [ ] `python Build_MSIX.py` ile son MSIX yeniden üretildi
- [ ] Gizlilik metnindeki yayıncı/e-posta alanları dolduruldu ve herkese açık URL'ye kondu
- [ ] Destek e-postası ve pazar/ücret seçimi doğrulandı
- [ ] Store ekran görüntüleri eklendi
- [ ] MSIX, açıklamalar ve sertifika notları Partner Center'a yüklendi
- [ ] Partner Center'ın otomatik paket doğrulaması hatasız geçti
- [ ] “Submit for certification” seçildi


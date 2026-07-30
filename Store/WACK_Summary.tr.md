# Yerel Windows Sertifika Testi Özeti

Test tarihi: 30 Temmuz 2026

Araç: Windows App Certification Kit 10.0.26100.7705

İlk tam taramada 24 testin 22'si geçti. Paket manifesti, uygulama sayısı,
kayıt defteri, kurumsal yetenekler, kaynak paketleri, UAC çalışma düzeyi ve
paket uyumluluğu testleri başarılı oldu.

## Düzeltilen uyarı

İlk rapor `Spiderpot_Ayarlar.exe` için PerMonitorV2 yüksek-DPI bildirimi istedi.
Her üç Windows EXE üretimine `Assets/Spiderpot.exe.manifest` eklendi ve yeni
paket üretildi. Son EXE içindeki gömülü manifest Windows SDK `mt.exe` aracıyla
okunarak aşağıdaki değerler doğrulandı:

- `requestedExecutionLevel`: `asInvoker`
- `dpiAware`: `true/pm`
- `dpiAwareness`: `PerMonitorV2`

## Kalan isteğe bağlı statik bulgu

WACK'in “Blocked executables” isteğe bağlı testi, PyInstaller'ın standart Python
çalışma zamanı içinde yer alan `cmd`, `reg`, `cdb`, `csi`, `dnx` metinlerini ve
`CreateProcessW` başvurusunu raporladı. Spiderpot bu sistem araçlarını çalıştırmaz.
Paket içinde süreç olarak yalnızca kendi `Spiderpot_Ayarlar.exe` ve
`Spiderpot_Sistem.exe` dosyaları arasında geçiş yapılır. Bu açıklama sertifika test
notlarına da eklendi.

## Paket bütünlüğü

`Build_MSIX.py --allow-placeholder`, MakeAppx ile manifest/payload doğrulaması
yapar, MSIX'i üretir ve
üretilen arşivi yeniden açarak `AppxManifest.xml`, `Spiderpot_Ayarlar.exe` ve
`Spiderpot_Sistem.exe` dosyalarının bulunduğunu doğrular.

Son teknik ön paket:

- Dosya: `dist/Spiderpot_1.0.0.0_x64_unsigned.msix`
- Boyut: `90,941,851` bayt
- SHA-256: `EB68552E4FD3D2BB2E68FB1586C28F817A6D64106F4B2A4137ED43FB6997E172`

Bu paket placeholder kimlik taşır. Partner Center ürün kimliği girildikten sonra
yeniden üretilecek son dosyanın hash değeri farklı olacaktır.
